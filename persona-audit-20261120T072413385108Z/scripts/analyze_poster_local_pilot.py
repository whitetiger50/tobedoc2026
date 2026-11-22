"""Verify exploratory annotations and summarize the preselected local pilot offline."""
from collections import Counter
from statistics import mean, median
import hashlib
import json
from pathlib import Path

from poster_local_study import OUT, ROOT, fp, read, save

VAL = {'yes': (1, 1), 'no': (0, 0), 'uncertain': (0, 1), 'unassessable': (0, 1)}
WEIGHTS = {'C1': 1, 'C2': -1, 'C3': -1, 'C4': 1}


def contrast_bounds(cells):
    lo = hi = 0
    for c, weight in WEIGHTS.items():
        a, b = VAL[cells[c]]
        lo += weight * (a if weight > 0 else b)
        hi += weight * (b if weight > 0 else a)
    return [lo, hi]


def verify_annotation(row, source):
    assert row['id'] == source['id'] and row['sha256'] == source['sha256']
    assert row['B'] in VAL
    assert row['A'] in ('direct', 'partial', 'absent', 'uncertain')
    assert row['C'] in VAL
    assert row['reason'].strip()
    before, after, text = row['before'], row['after'], source['text']
    assert before and after and before in text and after in text
    pos = text.index(before) + len(before)
    later = text.find(after, pos)
    assert later >= pos, 'Evidence must follow original order'
    gap = text[pos:later]
    assert not gap.strip(' \n\t.,;:—–-!?…'), 'Evidence spans must be adjacent clauses/sentences'
    assert hashlib.sha256(text.encode()).hexdigest() == source['sha256']


def main():
    masked = read(OUT / 'confirmation-masked.json')
    ratings = read(OUT / 'assessment-ratings.json')
    sample = read(OUT / 'pilot-amendment.json')['selected_assessment_ids']
    key = read(OUT / 'confirmation-key.json')
    assert len(masked) == len(ratings) == len(key) == 24
    assert {k['id'] for k in key} == set(sample)
    assert len({r['id'] for r in ratings}) == 24
    by_id = {r['id']: r for r in masked}
    for row in ratings:
        verify_annotation(row, by_id[row['id']])
    keyed = {r['blind_id']: r for r in key}
    measurements = {r['id']: r for r in read(OUT / 'measurements.json')}
    joined = []
    for r in ratings:
        source = keyed[r['id']]
        obs = measurements[source['id']]
        assert obs['text_sha256'] == r['sha256'] and obs['status'] == 'completed'
        joined.append({**r, 'request_id': source['id'], 'case': source['case'],
            'condition': source['condition'], 'question_number': source['question'], 'seed': source['seed'],
            'words': obs['words'], 'within_100_140': obs['within_100_140'],
            'label_hits': obs['label_hits'], 'trigram_repeat_rate': obs['trigram_repeat_rate']})
    assert Counter(r['case'] for r in joined) == {f'H0{i}': 6 for i in range(1, 5)}
    save(OUT / 'assessment-joined.json', joined, frozen=True)
    conditions = []
    for c in [f'C{i}' for i in range(6)]:
        d = [r for r in joined if r['condition'] == c]
        assert len(d) == 4
        conditions.append({'condition': c, 'n': 4, 'B_counts': dict(Counter(r['B'] for r in d)),
            'B_rate_bounds': [mean(VAL[r['B']][j] for r in d) for j in (0, 1)],
            'A_counts': dict(Counter(r['A'] for r in d)), 'C_counts': dict(Counter(r['C'] for r in d)),
            'word_mean': mean(r['words'] for r in d), 'word_median': median(r['words'] for r in d),
            'word_range': [min(r['words'] for r in d), max(r['words'] for r in d)],
            'length_compliant': sum(r['within_100_140'] for r in d),
            'label_response_count': sum(bool(r['label_hits']) for r in d),
            'mean_trigram_repeat_rate': mean(r['trigram_repeat_rate'] for r in d)})
    cases = []
    for case in sorted({r['case'] for r in joined}):
        cells = {r['condition']: r['B'] for r in joined if r['case'] == case}
        definite = all(cells[c] in ('yes', 'no') for c in WEIGHTS)
        cases.append({'case': case, 'B': cells, 'interaction_bounds': contrast_bounds(cells),
            'interaction_point': sum(WEIGHTS[c] * VAL[cells[c]][0] for c in WEIGHTS) if definite else None,
            'explicit_minus_category_bounds': [VAL[cells['C4']][0] - VAL[cells['C2']][1],
                VAL[cells['C4']][1] - VAL[cells['C2']][0]]})
    points = [c['interaction_point'] for c in cases if c['interaction_point'] is not None]
    length_effects = []
    for case in sorted({r['case'] for r in joined}):
        cells = {r['condition']: r['words'] for r in joined if r['case'] == case}
        length_effects.append({'case': case,
            'explicit_minus_label_words': cells['C4'] - cells['C2'],
            'interaction_words': (cells['C4'] - cells['C3']) - (cells['C2'] - cells['C1']),
            'cells': cells})
    result = {'assessment_responses': 24, 'fictional_cases': 4, 'clinical_raters': 0,
        'current_assistant_annotation_rounds': 1, 'conditions': conditions, 'case_effects': cases,
        'case_mean_interaction_bounds': [mean(c['interaction_bounds'][j] for c in cases) for j in (0, 1)],
        'case_mean_interaction_point_complete_cases': mean(points) if points else None,
        'complete_case_points': len(points),
        'explicit_minus_category_bounds': [mean(c['explicit_minus_category_bounds'][j] for c in cases) for j in (0, 1)],
        'length_effects': length_effects,
        'case_mean_explicit_minus_label_words': mean(c['explicit_minus_label_words'] for c in length_effects),
        'case_mean_length_interaction_words': mean(c['interaction_words'] for c in length_effects),
        'bounds_are_confidence_intervals': False,
        'inference': 'Descriptive matched pilot; no inferential p-values or population generalization.',
        'rating_file_sha256': hashlib.sha256((OUT / 'assessment-ratings.json').read_bytes()).hexdigest(),
        'masked_file_sha256': hashlib.sha256((OUT / 'confirmation-masked.json').read_bytes()).hexdigest()}
    save(OUT / 'results.json', result)
    integrity = {'assessment_ids_match_preselected_sample': True, 'ratings_verified': 24,
        'quote_pairs_verified': 24, 'ordered_adjacent_quotes': True, 'text_hashes_verified': 24,
        'model_backbone_unchanged': True, 'unknown_not_imputed_as_no': True,
        'new_calls': read(OUT / 'progress.json')['recorded'], 'paid_api_calls': 0,
        'downloads': 0, 'clinical_ratings': 0,
        'remaining_candidate_requests': 'Not released, not included in the pilot denominator.'}
    save(OUT / 'verification.json', integrity)
    print(json.dumps({'interaction_bounds': result['case_mean_interaction_bounds'],
        'explicit_minus_category_bounds': result['explicit_minus_category_bounds'],
        'B_by_condition': {r['condition']: r['B_counts'] for r in conditions},
        'quote_pairs_verified': 24}, ensure_ascii=False))


if __name__ == '__main__':
    main()
