"""Fetch a pinned-receipt Linux CPython 3.11 runtime from official release assets."""
import hashlib
import json
from pathlib import Path
import re
import tarfile
import urllib.request


def main():
    root=Path(__file__).resolve().parent.parent/'.runtime'
    url='https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ResearchForge-offline-setup'}),timeout=30) as r:release=json.load(r)
    assets=[asset for asset in release['assets'] if re.fullmatch(r'cpython-3\.11\..*x86_64-unknown-linux-gnu-install_only\.tar\.gz',asset['name'])]
    if len(assets)!=1:raise ValueError('ambiguous runtime asset')
    asset=assets[0]
    if not asset['browser_download_url'].startswith('https://github.com/astral-sh/python-build-standalone/releases/download/'):
        raise ValueError('unexpected upstream host')
    if asset['size']>200000000:raise ValueError('runtime size limit')
    target=root/asset['name']
    if not target.exists():
        with urllib.request.urlopen(asset['browser_download_url'],timeout=120) as r,target.open('xb') as out:
            while chunk:=r.read(1048576):out.write(chunk)
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    if asset.get('digest') and asset['digest']!='sha256:'+digest:raise ValueError('runtime digest mismatch')
    destination=root/'python311';destination.mkdir(exist_ok=True)
    with tarfile.open(target) as archive:archive.extractall(destination,filter='data')
    receipt={'source':asset['browser_download_url'],'release':release['tag_name'],'sha256':digest,'bytes':target.stat().st_size}
    (root/'python311_receipt.json').write_text(json.dumps(receipt,indent=2),'utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':main()
