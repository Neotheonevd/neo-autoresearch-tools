"""Explicit source-only distribution; no ambient workspace upload."""
import re
from pathlib import Path
import zipfile

from .store import sha

ALLOWED_FILES={'README.md','README.zh-CN.md','LICENSE','pyproject.toml','.gitignore'}
ALLOWED_DIRS={'researchforge','tests','docs','examples','.github','skills'}
SENSITIVE=re.compile(r'\b(?:sk-[A-Za-z0-9_-]{12,}|hf_[A-Za-z0-9]{20,})\b|[A-Za-z]:[\\/]Users[\\/][^<\s/\\]+')
FIGURE_ASSETS={'docs/assets/method-population.png','docs/assets/method-population.pptx',
               'docs/assets/motivation-portrait.png','docs/assets/motivation-portrait.pptx'}


def source_files(root):
    root=Path(root).resolve();result=[]
    # Never traverse private runtime trees: upstream tools may leave inaccessible
    # links there, and release discovery has no reason to inspect private data.
    candidates=[root/name for name in ALLOWED_FILES if (root/name).is_file()]
    for name in ALLOWED_DIRS:
        folder=root/name
        if folder.is_symlink():raise ValueError('linked directory in release')
        if not folder.is_dir():continue
        if name=='tests':candidates.extend(folder.glob('test_*.py'))
        else:candidates.extend(folder.rglob('*'))
    for path in sorted(candidates):
        relative=path.relative_to(root)
        if relative.name=='__pycache__' or '__pycache__' in relative.parts:continue
        if not path.is_file() or relative.suffix in {'.pyc','.sqlite3','.zip'}:continue
        if str(relative) not in ALLOWED_FILES and relative.parts[0] not in ALLOWED_DIRS:continue
        if relative.parts[0]=='tests' and not (len(relative.parts)==2 and relative.name.startswith('test_') and relative.suffix=='.py'):continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('linked file in release')
        if relative.name.startswith('.env') or any(part.startswith('local') for part in relative.parts):raise ValueError('private config in release')
        if relative.as_posix() in FIGURE_ASSETS:
            if path.suffix=='.png':
                if not path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('invalid figure PNG')
            else:
                with zipfile.ZipFile(path) as package:
                    for name in package.namelist():
                        if name.endswith(('.xml','.rels')) and SENSITIVE.search(package.read(name).decode('utf-8')):
                            raise ValueError('private content in figure package')
            result.append(path)
            continue
        text=path.read_text('utf-8')
        # Scanner itself contains patterns, never literal private credentials.
        if SENSITIVE.search(text):raise ValueError('possible credential/private absolute path: '+str(relative))
        result.append(path)
    return result


def bundle(root,target):
    root=Path(root).resolve();files=source_files(root);target=Path(target).resolve()
    if target.exists():raise ValueError('release already exists; do not overwrite')
    target.parent.mkdir(parents=True,exist_ok=True)
    manifest={path.relative_to(root).as_posix():sha(path) for path in files}
    import json
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,path.relative_to(root).as_posix())
        archive.writestr('SOURCE_MANIFEST.json',json.dumps(manifest,indent=2))
    return {'files':len(files),'sha256':sha(target),'path':str(target)}
