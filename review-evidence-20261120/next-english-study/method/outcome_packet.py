"""Write an aggregate-only final consultation for a fresh, tools-disabled Opus session."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
def read(f):return json.loads((BASE/f).read_text())
primary=read("results.json");sem=read("semantic/results.json");d=read("decision.json")
lex=read("lexical.json");patient=read("patient-anchor/aggregate.json")
packet={"valid_controls":read("calibration/results.json"),
        "primary":{j:{"contrasts":{k:v["counts"] for k,v in s["contrasts"].items()},"status":s["status"],
                       "score_dist":s["score_distribution"],"exact_repeat":s["repeat_exact"]} for j,s in primary["readers"].items()},
        "cross_reader":primary["cross_reader_exact"],"decisions":d,
        "semantic":{j:s["by_arm"] for j,s in sem["readers"].items()},
        "recap_agreement":sem["cross_reader"]["avoidable_recap"],
        "lexical":{a:{k:v["5"][k] for k in ("repeat_turns","eligible_turns","target_turns")} for a,v in lex["current"].items()},
        "clinical_5to12":{k:patient["primary"][k] for k in ("repeat_turns","eligible_turns","target_turns")},
        "clinical_and_nonclinical_all_available":{g:{w:[a["all"][w]["repeat_turns"],a["all"][w]["eligible_turns"]]
              for w in ("turns_5_12","from_5_to_end")} for g,a in read("patient-anchor/comparison-aggregate.json")["groups"].items()}}
instructions="""Provide independent critical interpretation as a final scientific collaborator. Exploratory eight paired fictional English schizophrenia outpatient cases, 12 fixed questions, single generation on GPT-6.1 Sol with each of three prompts. B=PatientHub PSYCHE-style benchmark with native history; T1=previous team; T2=compact English patient role that treats disclosed facts as shared, same data adapter as T1. Two independent blinded readers each read interviews twice with unchanged psychiatric adaptation of PATIENTSIM, plus two independent blinded semantic reads one each. Stable win requires win both rounds. Supremacy threshold both >=5/8, no meaningful guardrail breach or poor measurement. Fresh positive-control qualification requires >=3/4 stable downgrades; earlier defect experiment GPT 4/4 and Opus 0/4. Conservative development adoption needs both qualified and broadly competitive (>=6/8 stable ties/wins vs B with no entire stratum losing), improvement vs T1 and behavioral gates. Fixed rule and identically applied lexical test in patients vs synthetic: unmatched tasks, unequal verbal opportunity; do not rank by clinical distance. No external clinical validity claim. Independent source once-coded positive-agreement numbers are transcript-turn descriptive only. Summarize honest strongest scientific achievement and outstanding uncertainty. Reconcile surface repetition vs function, consider scale rater bias and seriousness of clinical inventions. If there is a labeling or arithmetic concern, say specifically what to check. Advise an evidenced disposition: research artifact vs deployment; do not recommend posthoc optimization on these eight. Under 260 words. Aggregate-only data follow.\n"""
if (BASE/"reconstruction/results.json").exists():
    rec=read("reconstruction/results.json")
    packet["exploratory_two_profile_targets_per_case"]={r:{k:v[k]["by_arm"] for k in ("all","excluding_control_correct")}
                                                        for r,v in rec["readers"].items()}
    instructions+="Additional exploratory diagnostic: matched true/foil/insufficient items about functioning, experience, and appraisal; no profile in readers. Q is questions alone. Recovering two selected facts per profile does not measure fidelity to schizophrenia as a whole.\n"
if (BASE/"external-task/release.json").exists():
    ext=read("external-task/release.json")
    # Never submit synthetic transcripts or traces for this final consultation.
    a=ext["analysis"]["english"]
    packet["external_trial_summary"]={"reference":ext["reference"],"means_by_arm":{
        arm:{t:s["mean"] for t,s in v["task"].items()} for arm,v in a["arms"].items()},
        "T2_pass_by_comparator":{arm:v["passes_both"] for arm,v in a["primary_patient_T2_vs_each"].items()},
        "loo_number_passing_each_comparator":{arm:sum(x["patient_T2_vs_others"][arm]["passes_both"]
            for x in a["leave_one_case_out"].values()) for arm in ("B","T1","Short")}}
    instructions+="External one-turn tasks are the published Pugh et al. 2024 storytelling and laundry prompts, clinically observed means 237/139 vs control 452/162. Their numbers reflect length and task pattern only. Is any positive finding specific to the patient reference or also explained by all synthetic arms undershooting both real groups? Identify what next independent evidence could actually change the development decision.\n"
(HERE/"outcome.txt").write_text(instructions+json.dumps(packet))
