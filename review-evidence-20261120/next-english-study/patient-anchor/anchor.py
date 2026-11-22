"""Local DAIS-C lexical recurrence audit. Stdout and saved files contain aggregates only."""
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from statistics import median
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
sys.path.insert(0, str(BASE))
from dais_turn_audit import document_text, get_exchange, QUESTIONS

FUNCTION = frozenset("""
a an the i me my mine myself we us our ours ourselves you your yours yourself yourselves
he him his himself she her hers herself it its itself they them their theirs themselves
this these that those there here which what who whom whose where when how why something
somebody someone anything anyone anybody everything everyone nothing nobody none
all any some each other another much many more most few both either neither
and or but for if then than as though because cos so while after before until when
at by from in into of off on onto out over through to up with without about around
is am are was were be been being do does did doing done have has had having
can could shall should will would may might must not no yes yeah yep right okay ok
i'm you're he's she's it's we're they're i've you've we've they've i'll you'll he'll she'll
we'll they'll i'd you'd he'd she'd we'd they'd isn't aren't wasn't weren't don't doesn't
didn't haven't hasn't hadn't won't wouldn't can't couldn't shouldn't mustn't
that's there's what's who's where's here's these those just really very quite too also
sort kind thing things like know mean well actually basically probably perhaps maybe
got get going say says said think thought feel sort yeah and hmm um uh er erm ah oh ay
""".split())
FILLER = frozenset("er erm um umm uh uhm ah oh ay mm mmm mhm hmm".split())
FRAGMENTS = frozenset("b c d f g h j k l m n p q r s t v w x y z wh th".split())
WORD = re.compile(r"[a-z]+(?:'[a-z]+)*|[0-9]+|[^a-z0-9'\s]+")
TAG = re.compile(r"<\s*(/?)\s*([a-z][a-z0-9]*)([^<>]*)>", re.I)
MARK = frozenset("gr ws tc dt".split())
MASK = frozenset("an inau lh ch sh sn cl fl noi".split())
REASK = re.compile(
    r"\b(?:repeat (?:that|the question|your answer|what)|(?:say|ask) (?:that|it|the question) "
    r"(?:again|once more)|what did you (?:say|just say)|didn'?t (?:quite )?(?:hear|catch) "
    r"(?:that|you)|in other words|rephrase|same question|say (?:it|that) another way)\b"
)


@dataclass(frozen=True)
class Speech:
    chunks: tuple
    clean: bool

    @property
    def tokens(self):
        return tuple(word for chunk in self.chunks for word in chunk)


def speech(tagged):
    chunks = []
    current = []
    hidden = []
    def boundary():
        if current:
            chunks.append(tuple(current))
            current.clear()
    def take(text):
        if hidden:
            return
        for token in WORD.findall(text.lower().replace("’", "'").replace("‘", "'")):
            if not token[0].isalpha() or token in FILLER or token in FRAGMENTS:
                boundary()
            else:
                current.append(token)
    pos = 0
    for m in TAG.finditer(tagged):
        take(tagged[pos:m.start()])
        close, name, _ = m.groups()
        name = name.lower()
        pos = m.end()
        if name in MARK:
            continue
        if name not in MASK:
            return Speech((), False)
        boundary()
        if close:
            if not hidden or hidden.pop() != name:
                return Speech((), False)
        else:
            hidden.append(name)
    take(tagged[pos:])
    boundary()
    return Speech(tuple(chunks), not hidden)


@lru_cache(maxsize=10000)
def grams(s, n):
    result = set()
    for chunk in s.chunks:
        for start in range(len(chunk)-n+1):
            phrase = chunk[start:start+n]
            if len(set(phrase)-FUNCTION) >= 2:
                result.add(phrase)
    return frozenset(result)


def reasks(new, old):
    if REASK.search(" ".join(new.tokens)):
        return True
    current = set(new.tokens)-FUNCTION
    previous = set(old.tokens)-FUNCTION
    common = current & previous
    if len(common) >= 2 and len(common)/len(current | previous) >= .60:
        return True
    return bool(grams(new, 4) & grams(old, 4))


@dataclass(frozen=True)
class Block:
    role: str
    value: Speech
    clean: bool


def parse(path):
    text = document_text(path)
    patient = path.stem[:-5]
    role_open = re.compile(r"<\s*("+re.escape(patient)+r"|int|doc|fam)\s*>",re.I)
    openings = list(role_open.finditer(text))
    blocks = []
    for i, match in enumerate(openings):
        role = match.group(1).lower()
        segment = text[match.end():openings[i+1].start() if i+1<len(openings) else None]
        ends = list(re.finditer(r"</\s*"+re.escape(role)+r"\s*>",segment,re.I))
        if len(ends) != 1:
            blocks.append(Block(role, Speech((),False), False))
            continue
        end = ends[0]
        utterance = speech(segment[:end.start()])
        # Stray content after closing the role makes the adjacent interval uncertain.
        clean = utterance.clean and (i==len(openings)-1 or not segment[end.end():].strip())
        blocks.append(Block(role, utterance, clean))
    group,_ = get_exchange(path)
    if group=="Q1":
        return None
    assert group in ("Q2","Q3")
    index=next(i for i,b in enumerate(blocks[:10]) if b.role=="int" and
               QUESTIONS[group] in " ".join(b.value.tokens))
    assert blocks[index+1].role==patient.lower()
    sequence = blocks[index:]
    patient_positions = [i for i,b in enumerate(sequence) if b.role==patient.lower()]
    return group,sequence,patient_positions


def inspect(person, n, maximum, prompt_filter):
    group,blocks,positions=person
    result=Counter()
    turn_words=[]
    limit=len(positions) if maximum is None else min(maximum,len(positions))
    for j in range(4,limit):
        result["target_turns"]+=1
        end=positions[j]
        target=blocks[end].value
        if blocks[end].clean:
            turn_words.append(len(target.tokens))
        else:
            result["invalid_target"]+=1
        if not grams(target,n):
            result["no_candidate_in_target"]+=1
            continue
        eligible=False
        hit=False
        exists_history=False
        has_lexical_pair=False
        for h in range(j-3,j):
            source=positions[h]
            if not source:
                continue
            interval=blocks[source-1:end+1]
            if any(not b.clean for b in interval) or any(
                b.role!=("int" if i%2==0 else blocks[end].role)
                for i,b in enumerate(interval)
            ):
                continue
            exists_history=True
            earlier=grams(blocks[source].value,n)
            if not earlier:
                continue
            has_lexical_pair=True
            old_prompt,new_prompt=blocks[source-1].value,blocks[end-1].value
            result["prior_answer_pair_candidates"]+=1
            if prompt_filter and reasks(new_prompt,old_prompt):
                result["prior_answer_pairs_screened_as_reask"]+=1
                continue
            eligible=True
            shared=grams(target,n)&earlier
            if prompt_filter:
                if shared and not shared-grams(new_prompt,n):
                    result["matching_pairs_fully_echoed_by_interviewer"]+=1
                shared-=grams(new_prompt,n)
            hit|=bool(shared)
        if not eligible:
            category="role_or_transcription" if not exists_history else (
                "no_candidate_in_previous" if not has_lexical_pair else "elicitation_filter")
            result[category]+=1
            continue
        result["opportunities"]+=1
        result["recurring_turns"]+=hit
    return group,result,turn_words


def stats(persons, n, maximum=12, prompt_filter=True):
    counts=Counter()
    eligible_people=positive_people=0
    lengths=[]
    opportunities_by_person=[]
    positive_turns_by_person=[]
    for _,person_count,size in (inspect(p,n,maximum,prompt_filter) for p in persons):
        counts.update(person_count)
        eligible_people+=bool(person_count["opportunities"])
        positive_people+=bool(person_count["recurring_turns"])
        lengths.extend(size)
        opportunities_by_person.append(person_count["opportunities"])
        positive_turns_by_person.append(person_count["recurring_turns"])
    reasons=["no_candidate_in_target","role_or_transcription","no_candidate_in_previous","elicitation_filter"]
    assert counts["target_turns"]==counts["opportunities"]+sum(counts[k] for k in reasons)
    return {"target_turns":counts["target_turns"],"eligible_turns":counts["opportunities"],
            "repeat_turns":counts["recurring_turns"],"eligible_people":eligible_people,
            "people_with_recurrence":positive_people,
            "exclusion_counts":{k:counts[k] for k in reasons},
            "pair_diagnostics":{k:counts[k] for k in (
                "prior_answer_pair_candidates","prior_answer_pairs_screened_as_reask",
                "matching_pairs_fully_echoed_by_interviewer")},
            "current_turn_with_invalid_bounds":counts["invalid_target"],
            "person_opportunities_median_range":[median(opportunities_by_person),min(opportunities_by_person),max(opportunities_by_person)],
            "person_recurrence_counts_median_range":[median(positive_turns_by_person),min(positive_turns_by_person),max(positive_turns_by_person)],
            "median_usable_tokens_in_clean_target":median(lengths) if lengths else None}


def score_dialogues(dialogues,n=5,maximum=12,prompt_filter=True):
    """Apply identical recurrence rule to intact synthetic Q/A dialogs; each dialog is a case.

    dialogues is an iterable of ordered lists of {'question':str,'answer':str}. All
    questions/answers are required. Do not pad, concatenate cases, or insert missing turns.
    maximum=None uses all turns from the fifth reply onward. Produces pure aggregate numbers.
    """
    persons=[]
    for dialogue in dialogues:
        blocks=[]
        for pair in dialogue:
            for role,field in (("int","question"),("respondent","answer")):
                if not isinstance(pair[field],str) or not pair[field].strip():
                    raise ValueError("Every clinical prompt and patient turn must be present")
                value=speech(pair[field])
                blocks.append(Block(role,value,value.clean))
        persons.append(("synthetic",blocks,list(range(1,len(blocks),2))))
    if not persons:
        raise ValueError("At least one dialogue is required")
    return stats(persons,n,maximum,prompt_filter)


def identity_check():
    a=speech("a parcel at <Lh>laughs</Lh> this front doorstep")
    b=speech("a parcel at this front doorstep")
    assert not grams(a,5) and grams(b,5)
    assert grams(speech("stored green <Gr>parcels in brown</Gr> cupboards"),5)
    assert not grams(speech("well you know what I mean"),5)
    assert not grams(speech("parcel on my erm front doorstep"),5)
    assert not grams(speech("parcel on my, front doorstep"),5)
    assert not grams(speech("parcel <AN>city</AN> on my front doorstep"),5)
    assert reasks(speech("Can you repeat that"), speech("How are you"))
    assert reasks(speech("Do parcels arrive Tuesday morning"),speech("How many parcels arrive Tuesday morning"))
    demo=[{"question":q,"answer":a} for q,a in [
        ("How are you?", "Fairly well"),("Do you work?", "The shed contains a narrow beam"),
        ("Where is the milk?", "It is waiting at home"),("What day?", "Thursday morning"),
        ("What broke?", "The shed contains a narrow beam")]]
    assert score_dialogues([demo])["repeat_turns"]==1
    assert score_dialogues([demo[:-1]])["target_turns"]==0


def run():
    identity_check()
    corpus=list(BASE.parent.glob("DAIS_C*/DAIS-C-Annotated - Upload/DAI-C-CL/Interactional/Full tagged pass"))
    assert len(corpus)==1
    files=sorted(p for p in corpus[0].glob("*-FULL.*") if not p.name.startswith("~$"))
    assert len(files)==15
    people=[]
    source=hashlib.sha256()
    for p in files:
        person=parse(p)
        if person:
            source.update(hashlib.sha256(p.read_bytes()).digest())
            people.append(person)
    assert Counter(x[0] for x in people)=={"Q2":7,"Q3":7}
    return {"source_archive_clinical_documents":len(files),"combined_source_digest":source.hexdigest(),
            "opening_groups":{"Q2":7,"Q3":7},
            "design_sha256":hashlib.sha256((HERE/"DESIGN.ko.md").read_bytes()).hexdigest(),
            "analysis_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "primary": stats(people,5),"primary_by_original_opening":{
                q:stats([p for p in people if p[0]==q],5) for q in ("Q2","Q3")},
            "sensitivities":{"four_tokens":stats(people,4),"six_tokens":stats(people,6),
                "without_prompt_filter":stats(people,5,prompt_filter=False),
                "all_turns_after_four":stats(people,5,maximum=None)}}

if __name__=="__main__":
    result=run()
    data=json.dumps(result,indent=2)+"\n"
    (HERE/"aggregate.json").write_text(data)
    print(data,end="")
