"""Stage a clearly synthetic, network-disabled upstream CLI acceptance task."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from researchforge.store import sha


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--node-linux',required=True);parser.add_argument('--image',required=True);parser.add_argument('--name',default='first')
    args=parser.parse_args();runtime=ROOT/'.runtime';runtime.mkdir(exist_ok=True)
    (runtime/'container.json').write_text(json.dumps({'node_linux':str(Path(args.node_linux).resolve()),'image':args.image}),'utf-8')
    import re
    if not re.fullmatch('[a-zA-Z0-9_-]+',args.name):raise ValueError('invalid probe name')
    base=runtime/'probe'/args.name
    if base.exists():raise ValueError('probe already exists; preserve receipt and use another name')
    repo=base/'repo';work=base/'work';repo.mkdir(parents=True);work.mkdir(parents=True)
    linux_repo='/workspace/'+repo.relative_to(ROOT).as_posix()
    linux_work='/workspace/'+work.relative_to(ROOT).as_posix()
    (repo/'run_eval.sh').write_text('#!/bin/sh\nprintf "mse_mean = 0.3616\\nmae_mean = 0.3650\\n"\n','utf-8',newline='\n')
    configdir=work/'.autosota/papers/mock-demo';configdir.mkdir(parents=True,exist_ok=True)
    cfg={'paper_title':'Offline adapter probe, not research results','paper_repo_url':'','repo_path':linux_repo,
         'venv_path':'','env_vars':'','eval_command':'bash run_eval.sh','eval_command_file':'run_eval.sh','eval_timeout_minutes':2,
         'gpu_devices':'0','baseline_metrics':{'ETTh1_MSE':0.3616,'ETTh1_MAE':0.3650},'primary_metric':'ETTh1_MSE',
         'metric_direction':'lower','metric_lower_bound':0.0,'metric_upper_bound':None,'target_improvement_pct':5.0,
         'max_iterations':1,'max_debug_attempts':1,'max_debug_minutes':1,'research_timeout_minutes':1,
         'research_model':'deepseek-v4-pro','openrouter_api_key':'','setup_notes':'Synthetic offline fixture; no improvement claim',
         'eval_output_format':'Parse mse_mean and mae_mean','known_levers':'No optimization; generate upstream prompt only'}
    (configdir/'config.yaml').write_text(json.dumps(cfg),'utf-8')
    venv=work/'.autosota/venv/bin';venv.mkdir(parents=True,exist_ok=True)
    interpreter='/workspace/.runtime/python311/python/bin/python3.11' if (runtime/'python311/python/bin/python3.11').exists() else '/usr/bin/python3'
    (venv/'python').write_text('#!/bin/sh\nexec '+interpreter+' "$@"\n','utf-8',newline='\n')
    (venv/'activate').write_text('export PATH="'+linux_work+'/.autosota/venv/bin:$PATH"\n','utf-8',newline='\n')
    task={'backend':'autosota','objective':'Offline actual AutoSOTA dry-run. Generate the upstream master prompt. Do not invoke a model.',
          'repo':repo.relative_to(ROOT).as_posix(),'workspace':work.relative_to(ROOT).as_posix(),'max_iterations':1,'max_seconds':120,
          'metric':{'name':'ETTh1_MSE','direction':'min','baseline':0.3616,'protocol_sha256':sha(repo/'run_eval.sh'),'split':'development'},
          'protected':{(repo/'run_eval.sh').relative_to(ROOT).as_posix():sha(repo/'run_eval.sh')},'outputs':['not-a-real-result.md']}
    (runtime/('probe-task-'+args.name+'.json')).write_text(json.dumps(task),'utf-8')
    launcher={'autosota':[sys.executable,str(ROOT/'researchforge/container_probe.py'),'mock-demo','--skip-onboard','--skip-export']}
    (runtime/'probe-launchers.json').write_text(json.dumps(launcher),'utf-8')
    print('Offline actual AutoSOTA probe staged; no provider credentials')


if __name__=='__main__':main()
