import argparse
import json
from pathlib import Path
import shutil
import subprocess

from .contracts import handoff, command, validate
from .export import bundle
from .gateway import serve
from .store import Store
from .worker import run_once, alive
from .results import collect_autosota


def read(path):return json.loads(Path(path).read_text('utf-8'))


def main():
    parser=argparse.ArgumentParser(description='ResearchForge: durable Argus/AutoSOTA experiment operations')
    parser.add_argument('--state',default='.runtime')
    commands=parser.add_subparsers(dest='action',required=True)
    p=commands.add_parser('init');p.add_argument('budget')
    commands.add_parser('status')
    p=commands.add_parser('pause');p.add_argument('--reason',default='operator pause')
    p=commands.add_parser('recover');p.add_argument('--gateway-stopped',action='store_true')
    p=commands.add_parser('submit');p.add_argument('task');p.add_argument('--root',default='.')
    p=commands.add_parser('plan');p.add_argument('task');p.add_argument('launchers');p.add_argument('--root',default='.');p.add_argument('--dry-run',action='store_true')
    p=commands.add_parser('worker');p.add_argument('launchers');p.add_argument('--root',default='.');p.add_argument('--dry-run',action='store_true')
    p=commands.add_parser('gateway');p.add_argument('config');p.add_argument('--port',type=int,default=18764)
    p=commands.add_parser('doctor');p.add_argument('launchers')
    p=commands.add_parser('collect');p.add_argument('workspace')
    p=commands.add_parser('export');p.add_argument('target');p.add_argument('--source',default=str(Path(__file__).resolve().parent.parent))
    args=parser.parse_args();store=Store(args.state)
    if args.action=='init':store.configure(read(args.budget));result=store.snapshot()
    elif args.action=='status':result=store.snapshot()
    elif args.action=='pause':store.pause(args.reason);result=store.snapshot()
    elif args.action=='recover':result={'reconcile':store.recover(alive,gateway_stopped=args.gateway_stopped)}
    elif args.action in {'submit','plan'}:
        spec=read(args.task);validate(spec,args.root)
        if args.action=='submit':handoff(spec,args.root);result={'job':store.submit(spec)}
        else:result={'argv':command(spec,args.root,read(args.launchers)[spec['backend']],args.dry_run),'launches_provider':False}
    elif args.action=='worker':result=run_once(store,args.root,read(args.launchers),dry_run=args.dry_run)
    elif args.action=='gateway':serve(store,read(args.config),args.port);return
    elif args.action=='collect':result=collect_autosota(args.workspace)
    elif args.action=='doctor':
        checks=[]
        for name,argv in read(args.launchers).items():
            executable=shutil.which(argv[0])
            checks.append({'backend':name,'executable_found':bool(executable),'executable':executable,
                           'paid_runtime_verified':False,'note':'doctor does not test credentials or start an optimization'})
        result={'checks':checks,'ready':all(row['executable_found'] for row in checks)}
    else:result=bundle(args.source,args.target)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
