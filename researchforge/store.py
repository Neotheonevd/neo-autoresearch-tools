"""Transactional project journal and conservative API accounting."""
import contextlib
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Halt(RuntimeError):
    pass


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,spec TEXT NOT NULL,state TEXT NOT NULL,
                    owner TEXT,updated REAL NOT NULL,pid INTEGER,reason TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,at REAL NOT NULL,kind TEXT NOT NULL,body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,category TEXT NOT NULL,state TEXT NOT NULL,
                    request_hash TEXT NOT NULL,reserved INTEGER NOT NULL,tokens INTEGER,created REAL NOT NULL,reason TEXT);
                CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY,receipt TEXT NOT NULL,hash TEXT NOT NULL);
            ''')

    @contextlib.contextmanager
    def db(self):
        db = sqlite3.connect(self.root / 'journal.sqlite3', timeout=20)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def event(db, kind, body):
        db.execute('INSERT INTO events(at,kind,body) VALUES(?,?,?)', (time.time(), kind, encoded(body)))

    def configure(self, spec):
        required = {'max_calls', 'max_tokens', 'max_seconds', 'max_inflight', 'category_tokens'}
        if set(spec) != required or any(type(spec[k]) is not int or spec[k] < 1 for k in required - {'category_tokens'}):
            raise ValueError('invalid hard budget')
        if not spec['category_tokens'] or any(type(v) is not int or v < 1 for v in spec['category_tokens'].values()):
            raise ValueError('explicit category budgets required')
        with self.db() as db:
            old = db.execute("SELECT value FROM settings WHERE key='budget'").fetchone()
            if old and old[0] != encoded(spec):
                raise Halt('budget is frozen; create a separately authorized window')
            if not old:
                db.executemany('INSERT INTO settings VALUES(?,?)', [('budget', encoded(spec)), ('started', str(time.time())), ('mode', 'active')])
                self.event(db, 'window_frozen', spec)

    def pause(self, reason):
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES('mode','paused')")
            self.event(db, 'paused', {'reason': reason})

    def reserve(self, category, request, ceiling):
        if type(ceiling) is not int or ceiling < 1:
            raise ValueError('positive conservative reservation required')
        failure = None
        key = uuid.uuid4().hex
        with self.db() as db:
            settings = dict(db.execute('SELECT key,value FROM settings'))
            if settings.get('mode') != 'active':
                raise Halt('window not active')
            budget = json.loads(settings['budget'])
            count, tokens, active = db.execute("SELECT COUNT(*),COALESCE(SUM(COALESCE(tokens,reserved)),0),COALESCE(SUM(state IN ('reserved','unknown')),0) FROM calls").fetchone()
            category_total = db.execute('SELECT COALESCE(SUM(COALESCE(tokens,reserved)),0) FROM calls WHERE category=?', (category,)).fetchone()[0]
            if category not in budget['category_tokens']:
                failure = 'unregistered call category'
            elif time.time() - float(settings['started']) >= budget['max_seconds']:
                failure = 'time budget exhausted'
            elif count >= budget['max_calls'] or tokens + ceiling > budget['max_tokens']:
                failure = 'global call/token budget exhausted'
            elif category_total + ceiling > budget['category_tokens'][category]:
                failure = category + ' budget exhausted'
            elif active >= budget['max_inflight']:
                # Backpressure must not pause unrelated already-running calls.
                raise Halt('inflight full; no provider request sent')
            if failure:
                db.execute("UPDATE settings SET value='paused' WHERE key='mode'")
                self.event(db, 'budget_stopped', {'reason': failure})
            else:
                db.execute("INSERT INTO calls VALUES(?,?,'reserved',?,?,NULL,?,NULL)",
                           (key, category, hashlib.sha256(encoded(request).encode()).hexdigest(), ceiling, time.time()))
                self.event(db, 'call_reserved', {'id': key, 'category': category, 'ceiling': ceiling})
        if failure:
            raise Halt(failure)
        return key

    def settle(self, key, tokens):
        if type(tokens) is not int or tokens < 0:
            raise ValueError('provider usage required')
        with self.db() as db:
            row = db.execute('SELECT state,reserved FROM calls WHERE id=?', (key,)).fetchone()
            if not row or row['state'] != 'reserved':
                raise Halt('call cannot be settled twice or guessed')
            db.execute("UPDATE calls SET state='complete',tokens=? WHERE id=?", (tokens, key))
            if tokens > row['reserved']:
                db.execute("UPDATE settings SET value='paused' WHERE key='mode'")
                self.event(db, 'reservation_exceeded', {'id': key, 'tokens': tokens})

    def uncertain(self, key, reason):
        with self.db() as db:
            db.execute("UPDATE calls SET state='unknown',reason=? WHERE id=? AND state='reserved'", (reason, key))
            db.execute("UPDATE settings SET value='paused' WHERE key='mode'")
            self.event(db, 'billing_unknown', {'id': key, 'reason': reason})

    def submit(self, spec):
        key = hashlib.sha256(encoded(spec).encode()).hexdigest()[:24]
        with self.db() as db:
            if not db.execute('SELECT 1 FROM jobs WHERE id=?', (key,)).fetchone():
                db.execute("INSERT INTO jobs(id,spec,state,updated) VALUES(?,?,'queued',?)", (key, encoded(spec), time.time()))
                self.event(db, 'job_queued', {'id': key, 'backend': spec['backend']})
        return key

    def claim(self, owner):
        with self.db() as db:
            mode = db.execute("SELECT value FROM settings WHERE key='mode'").fetchone()
            if not mode or mode[0] != 'active':
                return None
            # One writer in one owned workspace. Argus owns research planning.
            if db.execute("SELECT 1 FROM jobs WHERE state='running'").fetchone():
                return None
            row = db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY updated,id LIMIT 1").fetchone()
            if not row:
                return None
            db.execute("UPDATE jobs SET state='running',owner=?,updated=? WHERE id=?", (owner, time.time(), row['id']))
            self.event(db, 'job_claimed', {'id': row['id'], 'owner': owner})
            return {'id': row['id'], 'spec': json.loads(row['spec'])}

    def update_job(self, key, owner, *, pid=None, state=None, reason=''):
        with self.db() as db:
            row = db.execute('SELECT owner,state FROM jobs WHERE id=?', (key,)).fetchone()
            if not row or row['owner'] != owner or row['state'] != 'running':
                raise Halt('stale worker; write refused')
            db.execute('UPDATE jobs SET pid=COALESCE(?,pid),state=?,reason=?,updated=? WHERE id=?',
                       (pid, state or 'running', reason, time.time(), key))
            if state:
                self.event(db, 'job_finished', {'id': key, 'state': state, 'reason': reason})

    def recover(self, alive, *, gateway_stopped=False):
        """Never auto-replay a possibly paid job after a crash."""
        recovered = []
        with self.db() as db:
            if not gateway_stopped and db.execute("SELECT 1 FROM calls WHERE state='reserved'").fetchone():
                raise Halt('stop gateway before reconciling pending provider calls')
            for row in db.execute("SELECT * FROM jobs WHERE state='running'").fetchall():
                if row['pid'] and alive(row['pid']):
                    continue
                db.execute("UPDATE jobs SET state='needs_reconciliation',reason='worker lost; inspect backend receipts before native resume',updated=? WHERE id=?", (time.time(), row['id']))
                recovered.append(row['id'])
            for row in db.execute("SELECT id FROM calls WHERE state='reserved'").fetchall():
                db.execute("UPDATE calls SET state='unknown',reason='gateway interrupted' WHERE id=?", (row['id'],))
                recovered.append(row['id'])
            if recovered:
                db.execute("UPDATE settings SET value='paused' WHERE key='mode'")
                self.event(db, 'recovery_requires_reconciliation', {'ids': recovered})
        return recovered

    def snapshot(self):
        with self.db() as db:
            settings = dict(db.execute('SELECT key,value FROM settings'))
            if settings.get('mode')=='active' and time.time()-float(settings['started']) >= json.loads(settings['budget'])['max_seconds']:
                db.execute("UPDATE settings SET value='paused' WHERE key='mode'")
                self.event(db,'budget_stopped',{'reason':'window wall time exhausted'})
                settings['mode']='paused'
            return {'mode': settings.get('mode', 'unconfigured'), 'budget': json.loads(settings.get('budget', '{}')),
                    'jobs': [dict(row) for row in db.execute('SELECT id,state,pid,reason,updated FROM jobs ORDER BY updated')],
                    'usage': [dict(row) for row in db.execute('SELECT category,state,COUNT(*) AS calls,SUM(COALESCE(tokens,reserved)) AS tokens_or_reserved FROM calls GROUP BY category,state')]}
