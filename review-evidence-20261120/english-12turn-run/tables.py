"""Produce inspectable Korean result tables from verified data (no new ratings)."""
import json
from pathlib import Path
from statistics import median
from controls import words
from dispatch import HERE,read


def table(headers,rows):
    return "\n".join(["| "+" | ".join(headers)+" |","|"+"---|"*len(headers),*["| "+" | ".join(str(v) for v in row)+" |" for row in rows]])


def build():
    r=read(HERE/"results.json")
    b=read(HERE/"behavior/summary.json")
    sources=read(HERE/"key.json")
    reports=["# 영어 12턴 면담 판독 상세표","각 대괄호 안에 1·2회차의 원점수를 순서대로 표시한다. 점수 범위는 1–4이며, 높을수록 사례에 비추어 소통이 현실적이라고 판독했다. 승·동률·패는 같은 판독자의 두 회차 비교 방향이 일치했을 때 센다. 한 회차만 우세하면 불안정에 포함한다."]
    labels={"win":"승","tie":"동률","loss":"패","missing":"결측","unstable":"불안정"}
    for reader,x in r["readers"].items():
        reports += ["## "+("GPT" if reader=="gpt" else "Opus")+"의 보류 사례별 원점수",
                    table(["사례","B","T0","T1","T1 대 B","T1 대 T0"],[
                        [c,*[str(v[a]).replace("None","결측") for a in ("B","T0","T1")],
                         *[labels[x["contrasts"][k]["paired_by_case"][c]] for k in ("T1_vs_B","T1_vs_T0")]]
                        for c,v in sorted(x["heldout"].items())])]
        reports+=["### 조건별 점수 분포",table(["조건","1점","2점","3점","4점","결측"],
                    [[a,*[v["counts"].get(str(s),0) for s in range(1,5)],v["missing"]] for a,v in x["heldout_by_arm"].items()])]
        ctrl=x["control_pairs"]
        reports+=["### 개발 대조 원점수",table(["사례","원문","오류 주입","길이 변형","오류본 대 원문","길이본 대 원문"],
                    [[c,ctrl["Error"]["round_pairs"][c]["original"],ctrl["Error"]["round_pairs"][c]["variant"],
                      ctrl["Length"]["round_pairs"][c]["variant"],labels[ctrl["Error"]["variant_vs_original"][c]],
                      labels[ctrl["Length"]["variant_vs_original"][c]]] for c in sorted(ctrl["Error"]["round_pairs"])])]
    names={"clarify_yield":"모호한 질문에서 확인하고 차례를 넘김","answer_then_check":"모호한 질문에 답한 후 의미를 확인",
           "unnecessary_clarify":"명확한 질문에 불필요하게 확인","give_example":"요청에 구체적인 예를 제공",
           "contradiction":"명시적 중요 사실 모순","unanswered_repair":"후속 고정 질문으로 풀리지 않은 확인 요청"}
    reports+=["## 보류 면담의 별도 눈가림 행동 판독","각 셀은 양성 턴/사전 지정 기회다. 괄호는 별도로 유보한 턴 수다. 후속 질문의 미해결도 원래 모호한 질문의 기회를 분모로 삼았다.",
              table(["관찰 항목","B","T0","T1"],[[name,*[f"{v['positive']}/{v['opportunities']} ({v['uncertain']})"
                       for a in ("B","T0","T1") for v in [b["arms"][a][metric]]]] for metric,name in names.items()])]
    lengths={a:[] for a in ("B","T0","T1")}
    for k in sources:
        if not k["case"].startswith("H"):continue
        dlg=read(HERE/"blind"/(k["id"]+".json"))["dialogue"]
        lengths[k["arm"]].append(words([t["answer"] for t in dlg]))
    reports+=["## 보류 면담의 응답 길이","12개 환자 답변의 총 영어 단어 수를 면담별로 구했다. 각 조건은 같은 8사례다.",
              table(["조건","중앙값","범위"],[[a,median(ns),f"{min(ns)}–{max(ns)}"] for a,ns in lengths.items()]),
              "[원평점 및 계산 결과](results.json) · [행동 판독의 독립 기록](behavior/codes.json) · [최초 출력 무결성 검증](verification.json)"]
    (HERE/"TABLES.ko.md").write_text("\n\n".join(reports)+"\n")
if __name__=="__main__":
    build()
