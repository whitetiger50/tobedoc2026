"""Frozen fictional English cases and balanced assignments. No inference or network calls."""
import argparse
import json
import random
from pathlib import Path


ARMS = ("role_only_ablation", "development_v02")
PROFILES = ("usual", "associative", "low_elaboration")
OPENING = "Tell me about that visit in your own words, from the beginning through what happened at the end."
PROVENANCE = "authored_fictional_english_clinical_profile_pilot"

# Each turn concerns an everyday event and has several known, disclosable details.
# The setting in the first question is given to both the speaker and the reader.
CASES = {
    "C01": ("library", [
        "You visited a library with your cousin on Saturday to collect a reserved atlas.",
        "The librarian found a loose page while checking the atlas.",
        "Your cousin held the atlas while the librarian slipped the page into a sleeve.",
        "You collected the atlas and walked home with your cousin."],
        "Tell me how you and the librarian dealt with the loose page and how the visit ended."),
    "C02": ("market", [
        "You went to a market with a neighbour to collect a box of apples.",
        "The seller noticed that the cardboard handle had torn.",
        "The seller gave you a cloth bag and your neighbour helped move the apples.",
        "You carried the bag home and returned the empty box to the seller."],
        "Tell me what happened with the torn handle and how you got the apples home."),
    "C03": ("community garden", [
        "You met a friend at a community garden to plant two rosemary cuttings.",
        "One pot had a crack near its base.",
        "Your friend fetched another pot while you moved the soil with a trowel.",
        "You planted both cuttings and left the cracked pot beside the shed."],
        "Tell me what you and your friend did about the cracked pot and what happened next."),
    "C04": ("sports centre", [
        "You went to a sports centre with a colleague to play table tennis.",
        "The net on the first table came loose while you were warming up.",
        "An attendant led you to a second table and took the loose net away.",
        "You played one game at the second table before going home."],
        "Tell me what happened after the net came loose and how the visit ended."),
    "C05": ("print shop", [
        "You went to a print shop with a neighbour to collect posters for a street picnic.",
        "The top poster had a smudge across its date.",
        "The clerk printed a replacement while your neighbour rolled up the other posters.",
        "You checked the new date line and carried the posters to the community hall."],
        "Tell me how the problem with the poster was handled and what you did afterwards."),
    "C06": ("museum", [
        "You visited a museum with your aunt to see a collection of model ships.",
        "At an entrance a guide told you that the main staircase was closed.",
        "Your aunt asked for directions and the guide showed you another staircase.",
        "You reached the gallery by the other staircase and saw the model ships together."],
        "Tell me how you and your aunt reached the gallery and what you did there."),
}


def case_input(case_id, profile):
    _, facts, _ = CASES[case_id]
    communication = {
        "organization": "In everyday conversation you usually keep a line of thought in view.",
        "spontaneity": "You are willing to speak freely about this familiar visit.",
        "guardedness": "You are comfortable sharing all parts of this ordinary event.",
        "expression": "When you have time to tell a story, you usually expand on what happened.",
    }
    if profile == "associative":
        communication["organization"] = "In everyday conversation one impression readily leads your attention to another."
    elif profile == "low_elaboration":
        communication["expression"] = "When you have time to tell a story, you tend to stay with broad impressions of the experience."
    elif profile != "usual":
        raise ValueError("Unknown profile")
    return {
        "patient": {"case_id": case_id, "partition": "development", "provenance": PROVENANCE,
                    "facts": [{"id": f"E{i}", "kind": "background", "content": fact,
                               "patient_knows": True, "disclosure": "on_topic"}
                              for i, fact in enumerate(facts, 1)],
                    "self_understanding": "You remember this visit and are comfortable describing the experience."},
        "communication": communication,
    }


def questions(case_id):
    setting, _, followup = CASES[case_id]
    return [f"You mentioned a visit to a {setting}. {OPENING}", followup]


def assignments():
    dialogues = [(case, profile, arm) for case in CASES for profile in PROFILES for arm in ARMS]
    random.Random(61209).shuffle(dialogues)
    ids = list(range(1, len(dialogues) * 2 + 1))
    random.Random(18977).shuffle(ids)
    rows = []
    for case, profile, arm in dialogues:
        case_index = list(CASES).index(case)
        arm_index = ARMS.index(arm)
        for turn in (1, 2):
            repeat = (PROFILES[(case_index + arm_index) % 3] == profile
                      and turn == 1 + (case_index + arm_index) % 2)
            rows.append({"blind_id": f"R{ids.pop():03}", "dialogue_id": f"{case}-{profile}-{arm}",
                         "case_id": case, "profile": profile, "arm": arm, "turn": turn,
                         "question": questions(case)[turn-1], "repeat_read": repeat})
    return rows


def prior_exchange(row, rows, replies):
    if row["turn"] == 1:
        return []
    first = next(r for r in rows if r["dialogue_id"] == row["dialogue_id"] and r["turn"] == 1)
    answer = (replies / (first["blind_id"] + ".txt")).read_text(encoding="utf-8")
    if not answer.strip():
        raise ValueError("Turn two requires the complete first reply from this dialogue")
    return [{"question": first["question"], "answer": answer}]


def for_reader(row, rows, replies):
    history = prior_exchange(row, rows, replies)
    answer = (replies / (row["blind_id"] + ".txt")).read_text(encoding="utf-8")
    return {"history": history, "question": row["question"], "answer": answer}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("schedule", help="Operator-only key, never sent to readers")
    order = commands.add_parser("reading-order", help="Blind IDs without case, arm or profile labels")
    order.add_argument("reader", choices=("claude", "gpt", "psychiatrist1", "psychiatrist2"))
    order.add_argument("--repeat", action="store_true")
    case = commands.add_parser("case", help="JSON input for generation.py")
    case.add_argument("case_id", choices=CASES)
    case.add_argument("profile", choices=PROFILES)
    request = commands.add_parser("prepare", help="Prepare one generation request offline")
    request.add_argument("source_root", type=Path)
    request.add_argument("blind_id")
    request.add_argument("--replies", type=Path, help="Directory with exact replies as Rnnn.txt; required for turn two")
    blind = commands.add_parser("packet", help="Build the common human/LLM form from the exact interview")
    blind.add_argument("blind_id")
    blind.add_argument("replies", type=Path)
    args = parser.parse_args()
    if args.action == "schedule":
        result = assignments()
    elif args.action == "reading-order":
        result = [r["blind_id"] for r in assignments() if not args.repeat or r["repeat_read"]]
        result.sort()
        random.Random("english-clinical-profile:" + args.reader + str(args.repeat)).shuffle(result)
    elif args.action == "case":
        result = case_input(args.case_id, args.profile)
    else:
        rows = assignments()
        row = next((r for r in rows if r["blind_id"] == args.blind_id), None)
        if row is None:
            parser.error("Unknown scheduled ID")
        if args.action == "packet":
            from reader import packet
            print(json.dumps(packet(for_reader(row, rows, args.replies)), ensure_ascii=False, indent=2))
            return
        from generation import render
        if row["turn"] == 2 and args.replies is None:
            parser.error("Pass --replies for the second turn")
        history = []
        for exchange in prior_exchange(row, rows, args.replies):
            history.extend([{"speaker": "clinician", "text": exchange["question"]},
                            {"speaker": "patient", "text": exchange["answer"]}])
        trace = {"dialogue_id": row["dialogue_id"], "case_id": row["case_id"],
                 "condition": row["arm"], "turn_index": row["turn"]}
        result = render(args.source_root, case_input(row["case_id"], row["profile"]), history,
                        row["question"], row["arm"], trace)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
