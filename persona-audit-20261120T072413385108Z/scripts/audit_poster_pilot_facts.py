"""Offline target-fact expression inventory, NOT semantic fidelity or contradiction detection."""
import re
import json
from statistics import mean
from poster_local_study import OUT, read, save

RULES = {
    'H01': [
        ('wake at six', r'\b(?:wake|waking|woke|get up|getting up)\b[^.!?]{0,50}\b(?:six|6)\b'),
        ('eat yoghurt', r'\byog[hu]*urt\b'),
        ('cycle to bakery', r'\b(?:cycle|cycling|bike|bicycle)\b')],
    'H02': [
        ('check tickets', r'\bcheck(?:ing)?\b[^.!?]{0,30}\btickets?\b'),
        ('fill snack shelves', r'\b(?:fill(?:ing)?|stock(?:ing)?|restock(?:ing)?)\b[^.!?]{0,50}\b(?:snacks?|shelves)\b'),
        ('sweep lobby', r'\bsweep(?:ing)?\b[^.!?]{0,40}\blobby\b')],
    'H03': [
        ('sort incoming bags', r'\bsort(?:ing)?\b[^.!?]{0,40}\bbags?\b'),
        ('fold clean towels', r'\bfold(?:ing)?\b[^.!?]{0,35}\btowels?\b'),
        ('put away linen carts', r'\b(?:put(?:ting)?|store|storing)\b[^.!?]{0,50}\b(?:carts?|trolleys)\b')],
    'H04': [
        ('wake at nine', r'\b(?:wake|waking|woke|get up|getting up)\b[^.!?]{0,50}\b(?:nine|9)\b'),
        ('eat porridge', r'\bporridge\b'),
        ('take bus', r'\bbus\b')]
}


def main():
    plan = {'meaning': 'Presence of fixed lexical expressions only; absence may be paraphrase; a match does not prove a fact is true or unnegated.',
        'rules': RULES, 'frozen_before_assessment_text_review': True,
        'not_clinical_validation': True}
    save(OUT / 'fact-expression-plan.json', json.loads(json.dumps(plan)), frozen=True)
    measurements = {r['id']: r for r in read(OUT / 'measurements.json')}
    ids = read(OUT / 'pilot-amendment.json')['selected_assessment_ids']
    rows = []
    for ident in ids:
        r = measurements[ident]
        matches = []
        for fact, pattern in RULES[r['case']]:
            hit = re.search(pattern, r['text'], re.I)
            matches.append({'fact': fact, 'matched_expression': hit.group() if hit else None,
                'span': list(hit.span()) if hit else None})
        rows.append({'id': ident, 'case': r['case'], 'condition': r['condition'],
            'matches': matches, 'n_expressions': sum(m['span'] is not None for m in matches),
            'denominator': 3})
    summary = [{'condition': c, 'matched_expressions': sum(r['n_expressions'] for r in rows if r['condition'] == c),
        'total_target_expressions': 12} for c in [f'C{i}' for i in range(6)]]
    save(OUT / 'fact-expression-audit.json', {'rows': rows, 'summary': summary,
        'interpretation': 'Expression coverage, not fact accuracy, hallucination rate, or clinical fidelity.'})
    print(summary)


if __name__ == '__main__':
    main()
