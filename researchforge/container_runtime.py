"""Explicit Docker launcher for real AutoSOTA + real Claude Code.

The configuration is private and machine-specific. Only a local capability
token reaches the container; the real upstream credential stays in the gateway.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import uuid


def launch(config, args):
    root=Path(config['project_root']).resolve()
    work=Path.cwd().resolve()
    if not work.is_relative_to(root):raise ValueError('workdir outside owned project')
    token=json.loads(Path(config['connection_file']).read_text('utf-8'))['local_bearer']
    env=dict(os.environ)
    for key in list(env):
        if key.endswith(('API_KEY','AUTH_TOKEN')) or key.startswith(('OPENAI_','DEEPSEEK_','ANTHROPIC_','GH_','GITHUB_')):env.pop(key,None)
    env['ANTHROPIC_AUTH_TOKEN']=token
    job=os.environ.get('RF_JOB_ID',uuid.uuid4().hex)
    if len(job)!=24 or any(x not in '0123456789abcdef' for x in job):
        job=uuid.uuid4().hex[:24]
    name='researchforge-'+job
    mapped=[str(x).replace(str(root),'/workspace').replace(root.as_posix(),'/workspace').replace('\\','/') for x in args]
    argv=['docker','run','--rm','--init','--name',name,'--label','researchforge.job='+job,
          '--user','1000:1000','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
          '--memory','2g','--cpus','2','--pids-limit','128','--tmpfs','/tmp:rw,size=256m,mode=1777',
          '--mount',f'type=bind,source={root},target=/workspace']
    for key,target in [('node_linux','/opt/node'),('autosota_package','/opt/autosota'),
                       ('python_runtime','/opt/python'),('python_libraries','/opt/python-libs'),
                       ('claude_package','/opt/claude'),('shims','/opt/shims')]:
        argv.extend(['--mount',f"type=bind,source={Path(config[key]).resolve()},target={target},readonly"])
    settings={'HOME':'/tmp','CLAUDE_CONFIG_DIR':'/tmp/claude','MPLCONFIGDIR':'/tmp/matplotlib',
              'PYTHONPATH':'/opt/python-libs','PATH':'/opt/shims:/usr/local/bin:/usr/bin:/bin',
              'ANTHROPIC_BASE_URL':config['gateway_url'],'ANTHROPIC_MODEL':config['model'],
              'ANTHROPIC_DEFAULT_OPUS_MODEL':config['model'],'ANTHROPIC_DEFAULT_SONNET_MODEL':config['model'],
              'ANTHROPIC_DEFAULT_HAIKU_MODEL':config['model'],'CLAUDE_CODE_SUBAGENT_MODEL':config['model'],
              'MAX_THINKING_TOKENS':'0','CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING':'1',
              'CLAUDE_CODE_MAX_OUTPUT_TOKENS':'8192','DISABLE_PROMPT_CACHING':'1',
              'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC':'1',
              'AUTOSOTA_WORKSPACE':'/workspace/'+work.relative_to(root).as_posix()}
    for key,value in settings.items():argv.extend(['--env',key+'='+value])
    argv.extend(['--env','ANTHROPIC_AUTH_TOKEN','--workdir',settings['AUTOSOTA_WORKSPACE'],
                 '--entrypoint','/opt/node',config['image'],'/opt/autosota/dist/bin/autosota.js',*mapped])
    try:return subprocess.run(argv,env=env).returncode
    finally:
        # Also clean normal wrapper exits; the worker handles forced termination.
        subprocess.run(['docker','stop','--time','2',name],capture_output=True,check=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True)
    known,args=parser.parse_known_args()
    raise SystemExit(launch(json.loads(Path(known.config).read_text('utf-8')),args))


if __name__=='__main__':main()
