import { Stack, H1, H2, Text, Table, Divider, useHostTheme } from "cursor/canvas";
const studies = [["PATIENTSIM · NeurIPS 2025", "1:1 비교 없이 대화 전체 1–4", "임상의 비교: Realism AC1 .321 / AC2 .884", "주 평가 출발점. 응급실→정신과 적응을 명시", "https://proceedings.neurips.cc/paper_files/paper/2025/file/24945e3bdc7b3f4b2e64b9979a16f38e-Paper-Datasets_and_Benchmarks_Track.pdf"], ["PatientHub · 2026 프리프린트", "현실성 네 측면 각각 1–5", "GPT-4o 평가. 전문가 검증 없음", "보조 항목 참고. 원 실험의 상세 앵커 미확보", "https://arxiv.org/html/2602.11684v1"], ["SPBench / EasyMED · ACL 2026", "대화별 8항목. 부록 앵커 0–5", "86표본, 평가자 2명, 전체 r=.81", "주 지표 제외: 용어 개수·협조성에 편향", "https://aclanthology.org/2026.acl-long.1243.pdf"], ["PATIENT-Ψ · EMNLP 2024", "환자 유사성·대화 스타일 등 평정", "LLM과 전문가의 조건 순위가 반대", "LLM 채점 능력을 별도로 확인해야 하는 근거", "https://aclanthology.org/2024.emnlp-main.711.pdf"]];
export default function PatientSpeechRealismReview() {
 const t=useHostTheme();
 return <Stack gap={20} style={{padding:24,maxWidth:1200,margin:"0 auto",color:t.text.primary}}>
 <Text style={{color:t.text.secondary}}>문헌·공개 코드 검토 · 2026-11-18 · 우리 모델의 새 생성·채점 결과 없음</Text>
 <H1>한 대화가 해당 환자의 말처럼 들리는가</H1>
 <Text weight="semibold">주 평가 출발점: PATIENTSIM의 설정을 고려한 Realism 1~4점</Text>
 <Text>점수 앵커가 공개되어 있고 임상의 평가와 비교한 선례가 있다. 조현병에서 검증된 임상 척도는 아니다. 증상 중증도 점수로 발화 현실성을 대신 평가하지 않는다.</Text>
 <Table headers={["연구 / 원문","독립 채점 방식","사람과의 비교 근거","우리 연구의 판단"]} rows={studies.map(s=>[<a key={s[0]} href={s[4]} style={{color:t.text.link}}>{s[0]}</a>,s[1],s[2],s[3]])}/>
 <H2>PATIENTSIM 원 앵커의 한국어 요약</H2>
 <Table headers={["점수","설정의 환자에게 기대되는 의사소통"]} rows={[["1","매우 인공적이며 설정과 동떨어짐"],["2","부분적으로 자연스럽지만 비현실성이 눈에 띔"],["3","대체로 자연스럽고 설정에 맞으며 작은 어색함만 남음"],["4","매우 자연스럽고 해당 환자의 의사소통으로 설득력 있음"]]}/>
 <Text style={{color:t.text.secondary}}>확정 번역본이 아닌 원 앵커 요약. ED→정신과 맥락·한국어·판정 모델 변경은 적응으로 기록해야 한다. AC1·AC2는 일치도 계수이며 32.1%·88.4% 정확도가 아니다.</Text>
 <Divider/>
 <H2>실험에 적용할 때</H2>
 <Text>한 번에 환자 설정과 전체 대화 하나만 제시한다. 생성 프롬프트·조건명은 숨긴다. 조건 간 면담 과제와 질문 기회를 맞추고, 출력 길이를 강제로 동일하게 자르지 않는다.</Text>
 <Text>실제 출력 길이·잘림·질문 기회를 기록하고 길이에 따른 점수 변화를 확인한다. 설정에 없는 탈선이나 저항을 추가했다고 좋은 점수를 주는 지표가 아니다.</Text>
 <Text>PatientHub의 기본 공개 설정에는 원 실험의 현실성 네 항목 앵커가 없어 그대로 재현했다고 주장할 수 없다. SPBench의 전체 r=.81을 자연스러움 단일 항목 또는 조현병 평가의 검증으로 옮길 수 없다.</Text>
 <Text>초기 결과는 ‘해당 루브릭에서의 LLM 평가 점수’로 보고한다. 전문가 검증은 같은 대화·같은 항목을 점수를 숨겨 평가받아 추가한다.</Text>
 </Stack>;
}
