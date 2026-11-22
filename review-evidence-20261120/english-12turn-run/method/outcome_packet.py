"""Send only locked aggregate results to an independent final methods consultation."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(name):
    return json.loads((HERE.parent/name).read_text())
def prepare():
    results=read("results.json")
    behavior=read("behavior/summary.json")
    summary={}
    for judge,values in results["readers"].items():
        summary[judge]=dict(contrasts={k:v["counts"] for k,v in values["contrasts"].items()},
                            scores=values["heldout_distribution"],scores_by_condition=values["heldout_by_arm"],
                            repeat=values["heldout_exact_repeat"],status_counts=values["status_counts"],
                            error_degradation=values["control_pairs"]["Error"]["counts"],
                            length_preference=values["control_pairs"]["Length"]["consistent_preference"])
    packet=dict(readers=summary,crossjudge=results["heldout_cross_reader_exact_same_round"],
                behavior=behavior["arms"],bycase=behavior["by_case"],harm=behavior["contrast_harm"])
    text="""Independent final review. This is a completed exploratory student study of 8 matched fictional English outpatient schizophrenia profiles, one 12-turn interview per condition per profile on GPT-6.1 Sol medium. B used the matched-case PatientHub PSYCHE-style English template. T0 was the team original and T1 changed only a paragraph allowing a patient to ask for clarification and yield the turn rather than volunteering an anecdote. DAIS-C Q2 (5 of 7 actual people vs 1 of 21 prior synthetic repeats) was a development clue, never a target. Prelocked adapted single PATIENTSIM Realism_w_Profile 1-4 read by masked GPT high and Opus medium twice. Stable case wins require both rounds; suggest improvement only where both readers each have at least 5 of 8 stable wins, and defer on pooled within-reader 80% saturation, absent stable detection of any defective control, length-only repeated preference or recurrent harm. Prespecified ambiguity, clear questions and example opportunities; one separate blinded machine observer, quotes verified. Added four development controls for errors and four paired length edits independently assessed as neutral. You are seeing only aggregated numbers after data lock, from a consultation session separate from primary readers. Please independently identify what can and cannot be concluded, any arithmetic/interpretation traps, and a proportionate decision about adoption vs further validation. Distinguish the mechanism from overall clinical realism. No further experiments. In <=220 words.\n"""
    (HERE/"outcome.txt").write_text(text+json.dumps(packet))
if __name__=="__main__":
    prepare()
