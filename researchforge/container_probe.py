"""Offline invocation of the actual upstream AutoSOTA CLI, never a fake backend."""
import json
from pathlib import Path
import subprocess
import sys


def main():
    root=Path(__file__).resolve().parent.parent
    config=json.loads((root/'.runtime/container.json').read_text('utf-8'))
    args=sys.argv[1:]
    if '--dry-run' not in args and not any(arg in {'--help','--version'} for arg in args):
        raise ValueError('this acceptance launcher is offline only')
    mapped=[arg.replace(str(root),'/workspace').replace(root.as_posix(),'/workspace').replace('\\','/') for arg in args]
    work=Path.cwd().resolve().relative_to(root).as_posix()
    libraries='linuxpy311' if (root/'.runtime/python311/python/bin/python3.11').exists() else 'linuxpy'
    argv=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
          '--memory','1g','--cpus','2','--pids-limit','128','--tmpfs','/tmp:rw,size=128m',
          '--mount',f'type=bind,source={root},target=/workspace',
          '--mount',f"type=bind,source={config['node_linux']},target=/usr/local/bin/node,readonly",
          '--env','HOME=/tmp','--env','MPLCONFIGDIR=/tmp/matplotlib','--env','PYTHONPATH=/workspace/.runtime/'+libraries,
          '--env','AUTOSOTA_WORKSPACE=/workspace/'+work,
          '--workdir','/workspace/'+work,'--entrypoint','/usr/local/bin/node',config['image'],
          '/workspace/.runtime/vendor/autosota/package/dist/bin/autosota.js',*mapped]
    result=subprocess.run(argv)
    raise SystemExit(result.returncode)


if __name__=='__main__':main()
