"""Recompute pilot metrics from saved local model records, without inference."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .__main__ import digest
from eiv_experiment.run import covers, summarize, verify_freeze
from eiv_experiment.replay_validation import validate_bundle
from .integrity import validate_driver_transcript


def analyze(raw_path, cases_path):
    verify_freeze()
    raw_path, cases_path = Path(raw_path), Path(cases_path)
    manifest = json.loads(raw_path.with_suffix('.manifest.json').read_text())
    if manifest.get('raw_sha256') != digest(raw_path):
        raise ValueError('raw run incomplete or hash changed')
    if manifest['cases_sha256'] != digest(cases_path):
        raise ValueError('case hash differs from recorded run')
    selected = set(manifest['selected_case_ids'])
    cases = [json.loads(line) for line in cases_path.read_text().splitlines() if line.strip()]
    cases = [c for c in cases if c['case_id'] in selected]
    lookup = {c['case_id']: c for c in cases}
    rows = [json.loads(line) for line in raw_path.read_text().splitlines() if line.strip()]
    primary_rows = [r for r in rows if r['arm'] != 'direct_after_disclosure']
    validate_bundle(primary_rows, cases)
    validate_driver_transcript(rows, manifest, cases)
    seen = set()
    for row in rows:
        key = (row['case_id'], row['arm'])
        if key in seen or row['case_id'] not in selected or row['arm'] not in manifest['arms']:
            raise ValueError('duplicate or unknown pilot record')
        seen.add(key)
        case = lookup[row['case_id']]
        row['expected_decision'] = case['expected_decision']
        row['correct_resolved'] = row['decision'] == case['expected_decision']
        row['false_authorization'] = row['decision'] == 'allow' and case['expected_decision'] == 'deny'
        row['false_denial'] = row['decision'] == 'deny' and case['expected_decision'] == 'allow'
        versions = row['candidate_versions']
        first = versions[0]['case']['candidates'] if versions else []
        last = versions[-1]['case']['candidates'] if versions else []
        row['initial_candidate_count'] = len(first)
        row['initial_candidate_coverage'] = covers(first, case['latent_intent']['candidate'])
        row['final_candidate_coverage'] = covers(last, case['latent_intent']['candidate'])
        row['coverage_note'] = 'exact finite permission structure proxy, not human semantic judgment'
    if len(seen) != len(cases) * len(manifest['arms']):
        raise ValueError('missing pilot arms')
    summary = summarize(rows)
    summary['kind'] = 'local_llm_feasibility_not_confirmatory'
    summary['model'] = manifest['model']
    summary['model_digest'] = manifest['model_digest']
    summary['oracle'] = manifest['oracle']
    summary['raw_sha256'] = manifest['raw_sha256']
    summary['failure_counts'] = {arm: dict(Counter(e['kind'] for r in rows if r['arm'] == arm for e in r['errors'])) for arm in manifest['arms']}
    for arm, values in summary['metrics'].items():
        if arm != 'eiv':
            for key in list(values):
                if 'candidate' in key:
                    values[key] = None
    return summary, rows


def markdown(summary):
    lines = ['# Local LLM feasibility pilot', '',
             'Same installed Gemma 2 9B Q4_0 model, synthetic unreviewed labels, five template groups. This is an exploratory feasibility pilot, not the confirmatory experiment. Full-intent disclosure after any question prevents a claim about targeted question quality. Direct-after-disclosure receives free additional information and is a separate exploratory control.', '',
             '| Method | False allow / deny cases | False deny / allow cases | Correct / all | Abstain | Questions | Calls | Output tokens | Median seconds |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for arm, m in summary['metrics'].items():
        lines.append(f"| {arm} | {m['false_authorization_n']}/{m['latent_deny_n']} | {m['false_denial_n']}/{m['latent_allow_n']} | {m['correct_resolved_n']}/{m['n']} | {m['abstention_n']} | {m['questions_total']} | {m['model_calls']} | {m['output_tokens']} | {m['latency_seconds_median']:.1f} |")
    lines += ['', 'Schema failures and backend errors remain in the denominator and raw traces. External API spend is $0; local energy, hardware and user time are not valued. Re-running generation is not guaranteed bit-for-bit across runtime/hardware; replaying these raw outputs reproduces the reported analysis.', '', '## Paired descriptive uncertainty', '']
    for p in summary['paired']:
        lines.append(f"- EIV minus {p['comparator']}: correct-resolution difference {p['point']['correct_resolved_rate']:.3f}; family-bootstrap 95% percentile interval {p['family_bootstrap_95_percentile']['correct_resolved_rate']}. Only {p['family_n']} template groups; no generalization or significance claim.")
        lines.append(f"  Helps: {p['examples']['helps'] or 'none'}; ties: {p['examples']['no_change'] or 'none'}; harms: {p['examples']['harms'] or 'none'}.")
    m = summary['metrics']['eiv']
    lines += ['', f"EIV exact-structure intention coverage: initially {m['initial_candidate_coverage_n']}/{m['n']}; final all-case rate {m['final_candidate_coverage_rate_all']}. Logical equivalence can be missed by this proxy; a human semantic audit is still required.", '', 'Error counts: `' + json.dumps(summary['failure_counts'], sort_keys=True) + '`.', '', 'Raw data are the source of each result. Human label review, a question-specific oracle, independent families and a stronger-model replication are still required before testing the general research claim.']
    return '\n'.join(lines) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('raw', type=Path)
    p.add_argument('--cases', type=Path, default=Path('benchmark/v2/cases.jsonl'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('output exists; preserve analyses by choosing a new directory')
    summary, rows = analyze(a.raw, a.cases)
    a.output.mkdir(parents=True)
    (a.output/'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    (a.output/'scored.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    (a.output/'analysis.md').write_text(markdown(summary))
    print(json.dumps(summary['metrics'], indent=2))


if __name__ == '__main__':
    main()
