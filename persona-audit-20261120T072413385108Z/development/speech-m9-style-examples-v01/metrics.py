"""Deterministic surface-form proxies and copying risk flags, not clinical style labels."""
from collections import Counter
import re

DISTINCTIVE_TERMS=['가방','손목','샤워','피부','렌즈','안경']


def words(text):return re.sub(r'[^가-힣A-Za-z0-9\s]',' ',text).split()
def grams(text,n=3):
    w=words(text);return [tuple(w[i:i+n]) for i in range(len(w)-n+1)]


def overlap(answer,sources):
    target=grams(answer)
    reference={g for source in sources for g in grams(source)}
    return {'matched':sum(g in reference for g in target),'denominator':len(target),
            'ratio':sum(g in reference for g in target)/len(target) if target else None}


def risks(answer,examples):
    tokens=words(answer);norm=' '.join(tokens)
    full=[];long=[]
    answer4=set(grams(answer,4))
    for ex in examples:
        sample=' '.join(words(ex['patient']))
        if len(sample.replace(' ',''))>=12 and sample in norm:full.append(ex['reference_id'])
        shared=answer4 & set(grams(ex['patient'],4))
        if shared:long.append({'reference_id':ex['reference_id'],'shared_4_eojeol':[' '.join(g) for g in sorted(shared)]})
    return {'full_example_substring_matches':full,'shared_four_eojeol':long,
            'distinctive_reference_terms':[w for w in DISTINCTIVE_TERMS if w in answer]}


def turn_metrics(answer,question,facts,examples):
    return {'characters':len(answer),'eojeol':len(words(answer)),
            'profile_trigram':overlap(answer,[f['content'] for f in facts]),
            'question_trigram':overlap(answer,[question]),'copy_risks':risks(answer,examples)}


def summarize(rows):
    result={}
    for layer in ['all','neutral','prompted']:
        selected=[r for r in rows if layer=='all' or r['layer']==layer]
        result[layer]={'turns':len(selected),'patient_characters':sum(r['metrics']['characters'] for r in selected),
            'copy_risk_turns':sum(any(r['metrics']['copy_risks'].values()) for r in selected),
            'full_example_match_turns':sum(bool(r['metrics']['copy_risks']['full_example_substring_matches']) for r in selected),
            'four_eojeol_match_turns':sum(bool(r['metrics']['copy_risks']['shared_four_eojeol']) for r in selected),
            'distinctive_term_turns':sum(bool(r['metrics']['copy_risks']['distinctive_reference_terms']) for r in selected)}
        for field in ['profile_trigram','question_trigram']:
            matched=sum(r['metrics'][field]['matched'] for r in selected)
            denominator=sum(r['metrics'][field]['denominator'] for r in selected)
            result[layer][field]={'matched':matched,'denominator':denominator,'ratio':matched/denominator if denominator else None,
                'too_short_for_trigrams':sum(r['metrics'][field]['denominator']==0 for r in selected)}
    return result
