"""Run bounded backend work; research reasoning remains owned by Argus/AutoSOTA."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

from .contracts import command, handoff, inside, validate
from .store import Halt, sha
from .results import collect_autosota


def alive(pid):
    if os.name == 'nt':
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok and code.value == 259)
    try:
        os.kill(pid,0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def stop_child(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        result=subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=False)
        if result.returncode != 0 and process.poll() is None:
            # Use the exact child handle, not a guessed PID, when the host
            # denies taskkill. No unrelated process can be targeted here.
            process.kill()
    else:
        os.killpg(process.pid,signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def child_env():
    # The actual upstream key belongs only to the gateway process.
    return {k:v for k,v in os.environ.items() if not k.endswith(('API_KEY','AUTH_TOKEN'))
            and not k.startswith(('OPENAI_','ANTHROPIC_','DEEPSEEK_','GITHUB_','GH_'))}


def cleanup_job_container(key):
    import shutil
    if not shutil.which('docker'):return
    name='researchforge-'+key
    inspected=subprocess.run(['docker','inspect','--format','{{ index .Config.Labels "researchforge.job" }}',name],capture_output=True,text=True,check=False)
    if inspected.returncode==0 and inspected.stdout.strip()==key:
        subprocess.run(['docker','stop','--time','2',name],capture_output=True,check=False)


def run_once(store, root, launchers, *, dry_run=False, poll_seconds=1):
    owner = uuid.uuid4().hex
    job = store.claim(owner)
    if not job:
        return None
    key,spec = job['id'],job['spec']
    process = None
    receipt = {'job':key,'backend':spec['backend'],'dry_run':dry_run}
    folder = store.root / 'receipts' / key
    folder.mkdir(parents=True,exist_ok=True)
    try:
        validate(spec,root)
        handoff(spec,root)
        argv = command(spec,root,launchers[spec['backend']],dry_run)
        options = {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session':True}
        with (folder/'stdout.log').open('wb') as out, (folder/'stderr.log').open('wb') as err:
            environment=child_env();environment['RF_JOB_ID']=key
            process = subprocess.Popen(argv,cwd=inside(root,spec['workspace']),env=environment,stdin=subprocess.DEVNULL,
                                       stdout=out,stderr=err,**options)
            store.update_job(key,owner,pid=process.pid)
            started = time.monotonic()
            while process.poll() is None:
                mode = store.snapshot()['mode']
                if mode != 'active':
                    raise Halt('window paused; backend process stopped')
                if time.monotonic()-started >= spec['max_seconds']:
                    raise Halt('task wall time exhausted')
                store.update_job(key,owner)
                time.sleep(poll_seconds)
        # Check protected bytes before accepting any success claim.
        validate(spec,root)
        if process.returncode != 0:
            raise Halt('backend failed; inspect receipt, do not replay paid work')
        if spec['backend']=='autosota':
            imported=collect_autosota(inside(root,spec['workspace']))
            receipt['backend_artifacts']=imported['artifacts']
            if dry_run and not any(name.endswith('master_prompt.md') for name in imported['artifacts']):
                raise Halt('AutoSOTA dry-run exited without a generated master prompt')
        missing = [name for name in spec['outputs'] if not inside(inside(root,spec['workspace']),name).is_file()]
        if missing and not dry_run:
            raise Halt('backend exited without required artifacts: '+','.join(missing))
        receipt.update(returncode=process.returncode,outputs={name:sha(inside(inside(root,spec['workspace']),name)) for name in spec['outputs'] if name not in missing})
        state = 'dry_run_passed' if dry_run else 'awaiting_review'
        store.update_job(key,owner,state=state)
        receipt['state'] = state
    except BaseException as exc:
        if process:
            stop_child(process)
        receipt.update(state='needs_reconciliation',reason=str(exc))
        store.pause(str(exc))
        store.update_job(key,owner,state='needs_reconciliation',reason=str(exc))
        if isinstance(exc,(KeyboardInterrupt,SystemExit)):
            raise
    finally:
        if any('container_runtime.py' in part for part in locals().get('argv',[])):
            cleanup_job_container(key)
        (folder/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf-8')
    return receipt
