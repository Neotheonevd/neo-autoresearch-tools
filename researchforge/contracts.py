"""Portable bounded optimizer handoff; no secrets or free-form shell strings."""
from pathlib import Path
import re

from .store import encoded, sha


def inside(root, path):
    root = Path(root).resolve()
    path = (root / path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('path escapes owned project')
    return path


def validate(spec, root):
    required = {'backend','objective','repo','workspace','max_iterations','max_seconds','metric','protected','outputs'}
    if set(spec) != required:
        raise ValueError('task contract fields differ')
    if spec['backend'] not in {'autosota', 'argus'}:
        raise ValueError('unsupported research backend')
    if not isinstance(spec['objective'], str) or not spec['objective'].strip():
        raise ValueError('research objective required')
    if any(type(spec[k]) is not int or spec[k] < 1 for k in ['max_iterations','max_seconds']):
        raise ValueError('bounded iterations and wall time required')
    for key in ['repo','workspace']:
        if not inside(root, spec[key]).is_dir():
            raise ValueError('owned repo/workspace must exist')
    metric = spec['metric']
    if set(metric) != {'name','direction','baseline','protocol_sha256','split'} or metric['direction'] not in {'max','min'}:
        raise ValueError('metric/protocol identity required')
    if type(metric['baseline']) not in {int,float} or not re.fullmatch('[a-f0-9]{64}', metric['protocol_sha256']):
        raise ValueError('invalid baseline or protocol hash')
    if metric['split'] not in {'development','validation','heldout'}:
        raise ValueError('explicit evaluation split required')
    if not spec['protected'] or not spec['outputs']:
        raise ValueError('protected evaluators and required output artifacts required')
    for path, expected in spec['protected'].items():
        if sha(inside(root,path)) != expected:
            raise ValueError('protected artifact changed: ' + path)
    for path in spec['outputs']:
        inside(inside(root,spec['workspace']), path)
    return spec


def handoff(spec, root):
    validate(spec, root)
    work = inside(root, spec['workspace'])
    paper = work / 'paper'
    paper.mkdir(exist_ok=True)
    content = ('# Bounded optimization contract\n\n' + spec['objective'] + '\n\n'
               'Primary metric and fixed protocol:\n```json\n' + encoded(spec['metric']) + '\n```\n\n'
               'Use the shared evaluator and gateway. No scorer edits, direct provider calls, paid retries, '
               'task-specific gold lookup, publication or budget expansion. Preserve every negative result. '
               'Argus owns the research direction; optimize this bounded task only.\n\n'
               'Deliver: ' + ', '.join(spec['outputs']) + '\n')
    target = paper / 'target.md'
    if target.exists() and target.read_text('utf-8') != content:
        raise ValueError('task target already frozen; use a new workspace')
    target.write_text(content,'utf-8')
    contract = work / 'task.json'
    if contract.exists() and contract.read_text('utf-8') != encoded(spec):
        raise ValueError('task already frozen')
    contract.write_text(encoded(spec),'utf-8')
    return target


def command(spec, root, launcher, dry_run=False):
    validate(spec,root)
    if not isinstance(launcher,list) or not launcher or any(not isinstance(x,str) for x in launcher):
        raise ValueError('launcher must be explicit argv')
    if spec['backend'] == 'autosota':
        # Cwd owns the workspace across 0.2 and 0.3; --workspace is not
        # advertised by the pinned 0.2 CLI and must not be guessed.
        args = ['--repo',str(inside(root,spec['repo'])),
                '--skip-research','--max-iter',str(spec['max_iterations']),
                '--max-total-minutes',str(max(1,(spec['max_seconds']+59)//60))]
        if dry_run:
            args.append('--dry-run')
    else:
        args = ['--continuous','--bounded','--mission-width','1','--objective-file',
                str(inside(root,spec['workspace']) / 'paper/target.md'),'--daemon-fg']
        if dry_run:
            # Argus does not advertise an equivalent optimization dry-run.
            raise ValueError('Argus dry-run unsupported; inspect argv instead')
    return launcher + args
