"""Readable Korean tables from locked, machine-readable outcomes."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(name):return json.loads((HERE/name).read_text())
def table(head,rows):
    return "\n".join(["| "+" | ".join(head)+" |","|"+"---|"*len(head),
                      *["| "+" | ".join(map(str,row))+" |" for row in rows]])
def main():
    res=read("results.json"); sem=read("semantic/results.json");dec=read("decision.json");lex=read("lexical.json")
    rows=["# 영어 면담 후속 연구 상세표","승·동률·패에는 같은 사례의 두 회차 방향이 일치한 경우만 넣었다. 두 방향이 다르면 불안정이다. 각 보류 사례는 한 번만 생성했다."]
    comparison_labels={"win":"승","tie":"동률","loss":"패","unstable":"불안정","missing":"결측"}
    metric_labels={"avoidable_recap":"불필요한 재설명","evasive":"답할 수 있는 명료 질문 회피","consequential_invention":"중요 임상 사실 추가·모순",
                  "unsupported_stereotype":"설정에 없는 질환 전형 추가","first_recital":"첫 턴의 무관한 사실 나열",
                  "clarify_yield":"모호한 질문에 확인 후 차례 넘김","concrete_example":"예시 요청에 구체적인 사례 제시"}
    for r,x in res["readers"].items():
        name=r.upper() if r=="gpt" else "Opus"
        rows+=["## "+name+"의 면담 전체 평점","1–4점. 각 칸에는 첫째·둘째 회차 원점수를 순서대로 실었다.",
            table(["사례","B","T1","T2","T2 대 B","T2 대 T1"],[[c,*[str(v[a]) for a in ("B","T1","T2")],
                *[comparison_labels[x["contrasts"][k]["by_case"][c]] for k in ("T2_vs_B","T2_vs_T1")]]
                for c,v in sorted(x["by_case"].items())])]
        s=sem["readers"][r]
        rows+=["### "+name+"의 별도 행동 판독","양성/지정 기회. 괄호 안은 불확실·근거 결측 순서다.",
               table(["행동","B","T1","T2"],[[lab,*[f"{u['positive']}/{u['eligible']} ({u['uncertain']}, {u['missing']})"
                  for a in ("B","T1","T2") for u in [s["by_arm"][a][m]]]] for m,lab in metric_labels.items()])]
        rr=dec["by_reader"][r]
        rows+=["### T1 대비 T2의 사례별 변화",
               table(["사례","재설명 양성 수 차이","유보·결측을 고려한 범위","12턴 총 단어 T2/T1"],[
                   [c,s["contrasts"]["T2_vs_T1"]["avoidable_recap"]["by_case"][c]["observed_difference"],
                    rr["recap_uncertainty_by_case"][c],f"{v['T2']}/{v['T1']} ({v['T2']/v['T1']:.2f})"]
                   for c,v in sorted(lex["current_interview_words"].items())])]
    rows+=["## 서로 다른 판독자가 같은 행동을 찾았나",
           "양성 일치는 양쪽 양성 수의 두 배를 양쪽 양성 수의 두 배와 한쪽만 양성인 수의 합으로 나눴다. 양쪽 모두 명확하게 판정한 턴만 이 계산에 넣었다.",
           table(["행동","둘 다 양성","GPT만","Opus만","양성 일치","불확실 또는 결측"],[
             [lab,*[d["paired_counts"].get(k,0) for k in ("both_positive","gpt_only","opus_only")],
              f"{d['positive_agreement']:.1%}" if d["positive_agreement"] is not None else "양성 없음",
              d["paired_counts"].get("missing_or_uncertain",0)] for m,lab in metric_labels.items() for d in [sem["cross_reader"][m]]])]
    rows+=["## 같은 코드로 측정한 합성 면담의 구절 재사용","5–12번째 답이 직전 세 답과 내용 있는 연속 구절을 공유한 턴/평가 가능 턴이다. 같은 턴이 여러 구절을 공유해도 한 번으로 센다. 임상·비교 참여자의 동일 계산은 별도 자료에 있다.",
           table(["생성 표본","조건","4단어","5단어","6단어"],[[stage,a,*[f"{v[str(n)]['repeat_turns']}/{v[str(n)]['eligible_turns']}" for n in (4,5,6)]]
                    for stage,key in (("이전 개발 표본","previous"),("새 평가 표본","current")) for a,v in sorted(lex[key].items())]),
           "[실제 환자와 비임상 비교군 집계](patient-anchor/COMPARISON.ko.md) · [분모와 규칙](DESIGN.ko.md)"]
    (HERE/"TABLES.ko.md").write_text("\n\n".join(rows)+"\n")
if __name__=="__main__":main()
