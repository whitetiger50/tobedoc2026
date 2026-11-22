"""Build the one-page Korean research poster from the verified aggregate outputs."""
from html import escape
import json
from pathlib import Path
import tempfile


POSTER = Path(__file__).resolve().parent
STUDY = POSTER.parent
READERS = (("gpt", "GPT"), ("opus", "Opus"))
CONTRASTS = (("T1_vs_B", "T1 대 B", "주비교"), ("T1_vs_T0", "T1 대 T0", "수정 효과"))
COUNT_KEYS = ("win", "tie", "loss", "unstable", "missing")
BEHAVIORS = (("clarify_yield", "모호한 질문에서 확인 후 차례 양보"),
             ("answer_then_check", "모호한 질문에서 답한 뒤 확인"),
             ("unnecessary_clarify", "명료한 질문에서 불필요하게 확인"),
             ("give_example", "예를 요청받아 구체적인 예를 제시"),
             ("contradiction", "중요 사례 사실과 명백하게 모순"))


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def table(headers, rows, css=""):
    head = "".join("<th scope='col'>" + x + "</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in rows)
    return f"<table class='{css}'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def disposition(key, results, verify, behavior, neutral):
    readers = [results["readers"][r] for r, label in READERS]
    below = any(not r["contrasts"][key]["wins_at_least_5_of_8"] for r in readers)
    saturation = any(r["heldout_distribution"]["saturation_ge80"] is True for r in readers)
    error = any(r["control_pairs"]["Error"]["any_stable_error_downgrade"] is False for r in readers)
    length = any(r["control_pairs"]["Length"]["repeated_same_preference"] is True for r in readers)
    incomplete = (verify["reader_sessions_with_first_forms"] != 144 or verify["validated_first_turn_outputs"] != 336
                  or any(r["status_counts"].get("valid", 0) != 72 for r in readers))
    harms = behavior.get("contrast_harm", {}).get(key, {})
    harm = any(len(x["increased_cases"]) >= 2 for x in harms.values())
    pending = (incomplete or set(harms) != {"unnecessary_clarify","contradiction"}
               or set(neutral) != {"D01","D02","D03","D04"}
               or any(r["control_pairs"]["Length"]["repeated_same_preference"] is None for r in readers))
    reasons = [s for b,s in ((saturation,"평점 포화"),(error,"오류 대조 미검출"),(length,"길이 선호 반복"),
                             (harm,"불필요한 확인 또는 사실 모순 증가"),(incomplete,"누락 또는 무효 기록")) if b]
    if below and incomplete:
        return "우위 판정 유보", " · ".join(["관측된 승수 기준 미달", *reasons])
    if below:
        return "개선 기준 미충족", " · ".join(["판독자별 5승 기준 미달", *reasons])
    if reasons:
        return "우위 판정 유보", " · ".join(reasons)
    if pending or not any(neutral.values()):
        return "우위 판정 유보", "통제 또는 행동 자료로 판단하기 어려움"
    # Flag unresolved observations if they could change the two-case harm rule.
    if any(len(set(x["increased_cases"]) | set(x["cases_with_uncertainty"])) >= 2 for x in harms.values()):
        return "우위 판정 유보", "불확실한 행동 코딩이 악화 판정을 바꿀 수 있음"
    return "일관된 개선 신호", "두 판독자 모두 5승 이상, 사전 유보 기준 미해당"


def results_table(results):
    rows = []
    for key, label, _ in CONTRASTS:
        for reader, display in READERS:
            counts = results["readers"][reader]["contrasts"][key]["counts"]
            values = [counts.get(x,0) for x in COUNT_KEYS]
            if sum(values) != 8:
                raise ValueError("Each paired comparison must use eight held-out cases")
            rows.append([label, display, *map(str,values)])
    return table(["대비","판독자","승","동률","패","불안정","결측"], rows, "results")


def control_table(results):
    rows = []
    for reader, display in READERS:
        item = results["readers"][reader]
        dist = item["heldout_distribution"]
        if dist["n"]:
            n = max(dist["counts"].values())
            modes = ", ".join(f"{s}점" for s,hits in sorted(dist["counts"].items()) if hits == n)
            modal = f"{modes} · {n}/{dist['n']} ({100*n/dist['n']:.0f}%)"
        else:
            modal = "관측 없음"
        controls = item["control_pairs"]
        errors = controls["Error"]["counts"]
        pref = controls["Length"]["consistent_preference"]
        length = f"{sum(x=='longer_preferred' for x in pref.values())} / {sum(x=='shorter_preferred' for x in pref.values())}"
        rows.append([display, modal, f"{errors.get('loss',0)}/4", length])
    return table(["판독자","자연 평점 최빈 범주","오류본 하락","장문 / 단문 선호"], rows)


def behavior_table(behavior):
    if not behavior.get("arms"):
        return "<p>별도 행동 판독 집계가 없어 이 자료에서 확인할 수 없다.</p>"
    rows = []
    for key, label in BEHAVIORS:
        row = [label]
        for arm in ("B","T0","T1"):
            x = behavior["arms"][arm][key]
            cell = f"{x['positive']}/{x['opportunities']}"
            if x["uncertain"]:
                cell += f" <small>(?{x['uncertain']})</small>"
            row.append(cell)
        rows.append(row)
    return table(["관찰 행동","B","T0","T1"], rows, "behavior")


CSS = """
@page {size:400mm 276mm; margin:0}
*{box-sizing:border-box} :root{--ink:#152827;--muted:#455b59;--green:#005c56;--line:#c4d4d0}
body{margin:0;background:#e8eeec;color:var(--ink);font-family:"Apple SD Gothic Neo","Malgun Gothic","Noto Sans CJK KR",sans-serif;font-size:4.05mm;line-height:1.45;word-break:keep-all;font-variant-numeric:tabular-nums}
.tools{max-width:400mm;margin:0 auto;padding:7px 0;text-align:right}.tools button{margin-left:6px;padding:6px 12px;border:1px solid #98aaa5;border-radius:4px;background:#fff;color:#163e37;cursor:pointer}
.poster{width:400mm;min-height:276mm;position:relative;display:flex;flex-direction:column;margin:0 auto;background:white;padding:10mm 12mm 7mm}
header{padding-bottom:3.5mm;border-bottom:1.25mm solid var(--green)}
h1,h2,p{margin:0}h1{font-size:9.7mm;line-height:1.17;font-weight:800;letter-spacing:-.045em}
header p{margin-top:2mm;color:var(--muted);font-size:4.5mm}
.design{display:grid;grid-template-columns:1.02fr 1.3fr 1.02fr;margin:3.5mm 0 4mm;background:#edf5f2;padding:3mm 3.5mm;gap:5mm}
.design b{display:block;font-size:4.4mm;color:var(--green);margin-bottom:.5mm}
.columns{display:grid;grid-template-columns:1.08fr 1fr;gap:7mm}
.panel + .panel{margin-top:4mm}.panel h2{font-size:5.65mm;line-height:1.23;color:var(--green);padding-bottom:1.6mm;font-weight:750;letter-spacing:-.025em}
table{border-collapse:collapse;width:100%;font-size:3.95mm;text-align:center;line-height:1.33}
th{font-size:3.7mm;background:#f0f4f3;color:#344a47;font-weight:650}td,th{border-bottom:.3mm solid var(--line);padding:1.65mm 1.1mm}
th:first-child,td:first-child{text-align:left}.results td:nth-child(3){font-weight:750}
.results tbody tr:nth-child(3) td{border-top:.55mm solid #79958e}
.behavior td:first-child{width:54%}.behavior small{color:var(--muted);font-size:3.15mm}
.note{font-size:3.54mm;color:var(--muted);margin-top:1.45mm}
.decision{display:grid;grid-template-columns:1fr 1fr;gap:4mm;padding:3mm 4mm;background:#153e39;color:white;margin-top:4mm}
.decision b,.decision strong,.decision span{display:block}.decision strong{font-size:5.7mm;letter-spacing:-.025em}.decision b{color:#d0eae5;font-size:3.65mm}.decision span{font-size:3.55mm;color:#e6f2ed}
.limit{margin-top:2mm;font-size:3.8mm}
footer{margin-top:auto;padding-top:2.2mm;border-top:.35mm solid var(--line);font-size:3.15mm;color:#415853}
footer a{color:inherit;text-decoration:underline;text-underline-offset:.45mm}
@media print{html,body{margin:0;background:white;width:400mm}.poster{margin:0;break-inside:avoid}.tools{display:none}.poster[contenteditable]{outline:none}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def page(results, verify, behavior, neutral):
    if verify["reader_sessions_with_first_forms"] != results["unique_sessions"] or results["planned_cases"] != 8:
        raise ValueError("Verified and analyzed sources disagree")
    decisions = []
    for key, label, kind in CONTRASTS:
        status, reason = disposition(key, results, verify, behavior, neutral)
        decisions.append(f"<div><b>{kind} · {label}</b><strong>{status}</strong><span>{escape(reason)}</span></div>")
    completed = verify["reader_sessions_with_first_forms"]
    valid = sum(x.get("valid",0) for x in verify["reader_status"].values())
    n = sum(v is True for v in neutral.values())
    qa = ("검토 완료 " + str(len(neutral)) + "/4쌍, 중립성·길이 조건 충족 " + str(n) + "쌍"
          if neutral else "중립성 검토값 없음")
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>영어 조현병 모의 면담에서 발화기의 현실성 비교</title><style>{CSS}</style></head>
<body><nav class="tools" aria-label="문서 도구"><button type="button" onclick="editPoster()">문구 편집</button><button type="button" onclick="savePoster()">HTML 저장</button><button type="button" onclick="print()">인쇄 / PDF</button></nav>
<main class="poster" id="poster"><header><h1>영어 조현병 모의 면담에서 발화기의 현실성 비교</h1>
<p>8사례 짝비교에서 모호한 질문에 되묻고 기다리는 응답은 팀 원본 3/16회에서 수정판 11/16회로 늘었다. 전체 면담 현실성에서 수정판의 일관된 승리는 없었다.</p></header>
<div class="design"><div><b>개발 근거</b>DAIS-C Q2의 첫 반응이 되묻기였던 비율은 실제 환자 5/7, 팀 개발판 1/21이었다. 개발판은 입력 7개에 각각 3회 응답했다.</div>
<div><b>프롬프트 세 조건</b>B는 PatientHub의 PSYCHE식 영어 페르소나, T0는 팀 원본, T1은 T0에 질문이 모호하면 확인 후 차례를 넘길 수 있다는 지시를 더한 수정판이다.</div>
<div><b>동일한 면담 과제</b>새 가상 사례마다 세 조건에 같은 사실과 영어 질문 12개를 제시했다. GPT-6.1 Sol이 각 조건에서 자신의 앞선 문답을 이어받았다.</div></div>
<div class="columns"><section><div class="panel"><h2>같은 사례에서 T1의 평점은 더 높았는가?</h2>
{results_table(results)}<p class="note">사례 수 기준. 판독자별로 두 회차 모두 높은 경우에만 승, 두 회차 모두 같은 경우 동률이다. 두 회차의 비교 방향이 다르면 불안정으로 표시했다.</p></div>
<div class="panel"><h2>두 판독자가 차이를 감지할 수 있었는가?</h2>{control_table(results)}
<p class="note">최빈 범주는 보류 자연 면담 24개 × 2회 중 유효 평점 기준이다. 80% 이상이면 포화로 판단한다. 오류본 하락은 양회 모두 원본보다 낮은 개발 사례 수다. 길이 선호는 중립성이 확인된 쌍만 집계했다. {qa}.</p></div>
<div class="panel"><h2>무엇을 판독했는가?</h2><p>GPT-6.1 Sol과 Opus 5.5가 출처와 다른 평점을 가린 채 프로필과 면담 전체를 각 2회 읽었다. PATIENTSIM의 <i>Realism_w_Profile</i> 1–4점 앵커에서 응급실 환자라는 배경을 정신과 외래 환자로 바꿨다.</p></div></section>
<section><div class="panel"><h2>면담에서 실제로 나타난 대화 행동</h2>{behavior_table(behavior)}
<p class="note">별도 LLM 한 대가 출처를 가리고 판독했다. 분자는 확인된 턴, 분모는 미리 지정한 관찰 기회다. 사실 모순은 전체 턴을 대상으로 했다. 괄호의 ?는 해당 분모 안의 불확실한 턴 수다.</p></div>
<div class="panel"><h2>어떻게 개선을 판정했는가?</h2><p>각 대비에서 두 판독자 모두 8사례 중 5사례 이상 승리해야 한다. 평점 포화, 오류 대조 미검출, 중립 길이 대조에서 같은 편향이 2사례 이상 반복되거나 불필요한 확인·사실 모순이 같은 항목에서 2사례 이상 증가하면 우위 판정을 유보한다.</p></div>
<div class="panel"><h2>자료 검증</h2><p>최초 생성 환자 답변 {verify['validated_first_turn_outputs']}/336개, 출처를 가린 면담 자료 {verify['masked_inputs']}/36개. 판독 세션 {completed}/144회, 유효 평점 {valid}/144개. 개발용 원본과 변형은 보류 8사례의 승수에서 제외했다.</p></div></section></div>
<div class="decision">{''.join(decisions)}</div>
<p class="limit">전체 현실성에서 GPT는 8사례 중 5사례, Opus는 6사례에서 B에 T1보다 높은 점수를 두 번 모두 부여했다. 두 판독자의 같은 회차 원점수 일치는 9/48이었다. 실제 환자 재현도와 전문의 일치도는 독립 검증이 필요하다.</p>
<footer>척도 · <a href="https://proceedings.neurips.cc/paper_files/paper/2025/file/24945e3bdc7b3f4b2e64b9979a16f38e-Paper-Datasets_and_Benchmarks_Track.pdf">PATIENTSIM, NeurIPS 2025</a> &nbsp; 비교 페르소나 · <a href="https://github.com/Sahandfer/PatientHub/blob/54d5c8761a9055a1e86d153715607ef9fa26358a/patienthub/clients/psyche.py">PatientHub, PSYCHE client · 54d5c876</a> &nbsp; 개발 관찰 · <a href="https://reshare.ukdataservice.ac.uk/855021/">Delgaram-Nejad 외, DAIS-C</a></footer>
</main><script>
function editPoster(){{const p=document.getElementById("poster");p.contentEditable=p.isContentEditable?"false":"true";if(p.isContentEditable)p.focus();}}
function savePoster(){{const p=document.getElementById("poster");p.removeAttribute("contenteditable");const data=new Blob(["<!doctype html>\\n",document.documentElement.outerHTML],{{type:"text/html;charset=utf-8"}});const url=URL.createObjectURL(data),a=document.createElement("a");a.href=url;a.download="POSTER.ko.html";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}}
</script></body></html>"""


def build():
    results = read(STUDY/"results.json")
    verify = read(STUDY/"verification.json")
    optional = [STUDY/"behavior/summary.json", STUDY/"controls/neutrality.json"]
    content = page(results, verify, *(read(p) if p.is_file() else {} for p in optional))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=POSTER, delete=False) as temp:
        temp.write(content)
        target = Path(temp.name)
    target.replace(POSTER/"POSTER.ko.html")


if __name__ == "__main__":
    build()
