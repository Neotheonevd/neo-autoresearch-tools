"""Import upstream artifacts without trusting a self-reported score as official."""
import json
from pathlib import Path
from .store import sha


def collect_autosota(workspace):
    work=Path(workspace).resolve();artifacts={};rows=[]
    for pattern in ['**/scores.jsonl','**/master_prompt.md','**/final_patch.diff','**/evaluation_verdict.json']:
        for path in work.glob(pattern):
            if not path.is_file() or not path.resolve().is_relative_to(work):continue
            relative=path.relative_to(work).as_posix()
            artifacts[relative]=sha(path)
            if path.name=='scores.jsonl':
                for number,line in enumerate(path.read_text('utf-8').splitlines(),1):
                    if line.strip():
                        value=json.loads(line)
                        if not isinstance(value,dict):raise ValueError('invalid AutoSOTA score row')
                        rows.append({'artifact':relative,'line':number,'backend_reported':value})
    report={'backend':'autosota','artifacts':artifacts,'reported_scores':rows,'official_score_verified':False,
            'automatic_promotion':False}
    (work/'backend_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    return report
