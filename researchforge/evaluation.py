"""Receipt validation and fixed-protocol paired comparisons; never invent labels."""
import math


def compare(baseline, candidate, protocol, cases):
    if len(cases) != len(set(cases)) or not cases:
        raise ValueError('fixed unique case manifest required')
    for report in [baseline,candidate]:
        if report.get('protocol_sha256') != protocol or report.get('denominator') != len(cases):
            raise ValueError('protocol/denominator mismatch')
        rows = report.get('rows',[])
        if len(rows) != len(cases) or {r['case'] for r in rows} != set(cases):
            raise ValueError('incomplete or selected cases')
        if any(type(r.get('correct')) is not bool for r in rows):
            raise ValueError('official boolean results required')
    old = {r['case']:r['correct'] for r in baseline['rows']}
    new = {r['case']:r['correct'] for r in candidate['rows']}
    wins = [case for case in cases if new[case] and not old[case]]
    losses = [case for case in cases if old[case] and not new[case]]
    return {'denominator':len(cases),'baseline_correct':sum(old.values()),'candidate_correct':sum(new.values()),
            'wins':wins,'losses':losses,'net':len(wins)-len(losses),
            'interpretation':'development improvement' if len(wins)>len(losses) else 'no net development improvement',
            'sota_claim':False}


def accepts(metrics, objective):
    """A score win must satisfy every declared guardrail."""
    primary = objective['primary']
    for name in [primary,*objective.get('guardrails',{})]:
        if type(metrics.get(name)) not in {int,float} or not math.isfinite(metrics[name]):
            return False
    direction = objective['direction']
    if direction not in {'max','min'}:
        raise ValueError('invalid metric direction')
    if (metrics[primary]-objective['baseline']) * (1 if direction=='max' else -1) <= 0:
        return False
    for name,rule in objective.get('guardrails',{}).items():
        if 'min' in rule and metrics[name]<rule['min'] or 'max' in rule and metrics[name]>rule['max']:
            return False
    return True
