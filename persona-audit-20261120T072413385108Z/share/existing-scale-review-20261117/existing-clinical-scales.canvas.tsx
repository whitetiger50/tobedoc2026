import { Stack, Row, H1, H2, Text, Table, Select, Divider, useState, useHostTheme } from "cursor/canvas";
const evidence = {"date": "2026-11-17", "status": "Existing-item candidates identified; evaluator validity is not inherited", "new_model_outputs": false, "candidates": [{"id": "bprs", "name": "BPRS-E 4.0 원항목", "decision": "개발용 독립 채점 우선 후보", "scoring": "선정한 원항목별 1~7; NA 별도. 합산 단축척도 없음.", "scope": "9 의심 · 10 환각 · 11 비정상적 사고내용 · 15 개념적 와해", "preserve": "원 정의·앵커·평정 원칙 유지; 대화 전체에서 한 평점", "constraint": "15번의 자동 판독 근거는 약함. 전체 척도 성능을 항목 성능으로 옮기지 않음.", "source": "https://adai.uw.edu/instruments/pdf/BPRSmanual.pdf", "source_read": "29쪽 매뉴얼 전체의 평정 조건·선정 항목 확인", "llm_evidence": "https://doi.org/10.1093/schbul/sbag084"}, {"id": "psyrats", "name": "K-PSYRATS", "decision": "증상 내용의 상세 평가 후속 후보", "scoring": "기존 환청·망상 하위척도 원항목/원합산법 확보 후 사용", "scope": "환청·망상 경험의 여러 차원; 사고형식 척도 아님", "preserve": "정식 한국어판 문항·앵커·면담 조건을 유지", "constraint": "한국어 원양식 전체 미확보. 검토 범위에서 직접 LLM 검증을 찾지 못함.", "source": "https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001224101", "source_read": "한국어판 원저 초록·서지 확인; 전체 매뉴얼 확보 아님"}, {"id": "tald", "name": "TALD", "decision": "사고형식 후속 후보", "scoring": "원항목 0~4 유지 시 가능성 있음; 새 앵커 작성 금지", "scope": "관찰 가능한 사고형식과 주관적 경험 구분", "preserve": "원 매뉴얼·면담 요구·정보원 유지", "constraint": "긴 면담·음성 정보 체계의 연구. 정식 영어 전체 매뉴얼 미확보.", "source": "https://link.springer.com/article/10.1007/s11042-026-21401-8", "source_read": "ClearThought 원저 방법·결과·자료 가용성 확인"}, {"id": "tlc", "name": "TLC", "decision": "짧은 대화에 원점수 강행하지 않음", "scoring": "일부 항목의 빈도·관찰량 전제", "scope": "사고·언어·의사소통 현상", "preserve": "빈도 경계를 임의 재설정하거나 블록 평균으로 대체하지 않음", "constraint": "짧은 텍스트의 충분한 관찰량 문제. Global rating이 개별 현상을 대체하지 못함.", "source": "https://pubmed.ncbi.nlm.nih.gov/3764363/", "source_read": "1986 원문 검토"}, {"id": "tli", "name": "TLI", "decision": "현재 텍스트 면담에는 제외", "scoring": "표준 그림 발화·시간·확인 절차 필요", "scope": "표준화 발화 과제의 사고·언어", "preserve": "텍스트 상황으로 그림을 대체하거나 생성 시간을 발화 시간으로 환산하지 않음", "constraint": "원 절차와 상세 매뉴얼 확보 필요.", "source": "https://doi.org/10.1192/bjp.181.4.326", "source_read": "원저 Method·Appendix; 상세 매뉴얼 미확보"}, {"id": "tdi", "name": "TDI", "decision": "현 팀 조건에서 제외", "scoring": "원 총점은 Rorschach/WAIS 자료에 별도 산출법", "scope": "생각 이탈의 범주·심각도", "preserve": "원 분모를 채팅 턴 수로 바꾸지 않음", "constraint": "과제·문맥 확인·고도 판독 훈련의 부담.", "source": "https://academic.oup.com/schizophreniabulletin/article-pdf/12/3/483/5279477/12-3-483.pdf", "source_read": "원 매뉴얼 도입·절차·말미 산출식 확인"}, {"id": "panss-saps", "name": "PANSS / SAPS·SANS 전체", "decision": "텍스트 추정 총점 제외", "scoring": "일부 항목만 보고 전체 점수를 만들지 않음", "scope": "질환 전반의 증상과 관찰 행동", "preserve": "비언어·음성 정보를 텍스트에서 추측하지 않음", "constraint": "이번에 전체 매뉴얼과 항목별 LLM 근거를 모두 검토한 것은 아님.", "source": "https://academic.oup.com/schizophreniabulletin/article/13/2/261/1919795", "source_read": "원척도 서지 및 범위 검토; 전체 앵커 검토 미완료"}, {"id": "amdp", "name": "AMDP", "decision": "보조 후보; 우선순위 낮음", "scoring": "원 항목과 평가 불가 구분을 유지해야 함", "scope": "다양한 정신병리 현상", "preserve": "관찰 불가능 항목을 부재로 대입하지 않음", "constraint": "직접 LLM 연구는 3개 연기 시나리오. 원 매뉴얼과 한국어 적용 준비 부족.", "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13342660/", "source_read": "원저 방법·결과 확인"}], "critical_studies": [{"name": "Chen, Horga & Escola 2026", "url": "https://doi.org/10.1093/schbul/sbag084", "location": "Methods; Overall Accuracy; Foreign Language Interviews", "finding": "BPRS LLM 직접 평정. 비구조화 면담과 항목 15의 한계가 중요.", "not_established": "현 모델의 항목별 한국어 합성 대화 타당성"}, {"name": "K-PSYRATS 2007", "url": "https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001224101", "location": "원저 초록·서지", "finding": "한국어 임상 척도의 검증 존재", "not_established": "LLM 판독; 본 검토에서의 원양식 전체 확보"}, {"name": "ClearThought 2026", "url": "https://link.springer.com/article/10.1007/s11042-026-21401-8", "location": "Sections 2.1, 3, 4.3; Data Availability", "finding": "원 TALD에 기초한 항목별 LLM 평정 선례", "not_established": "짧은 한국어 텍스트에서 전체 TALD 재현"}, {"name": "Pugh et al. 2024", "url": "https://ckchandler.github.io/files/publications/pugh_psychresearch.pdf", "location": "Sections 1.1–1.2, 2.1.2", "finding": "발화 과제의 기존 연구 루브릭을 LLM이 평가", "not_established": "TLC 원항목을 같은 짧은 발화에 직접 채점한 연구가 아님"}]};
export default function ExistingScaleOptions() {
  const theme=useHostTheme();
  const [selected,setSelected]=useState("bprs");
  const current=evidence.candidates.find(s=>s.id===selected)||evidence.candidates[0];
  return <Stack gap={20} style={{padding:24,maxWidth:1200,margin:"0 auto",color:theme.text.primary}}>
    <Text style={{color:theme.text.secondary}}>원척도 유지 여부 검토 · 2026-11-17 · 새 생성·채점 결과 없음</Text>
    <H1>증상 내용 평가용 검토 — 발화 현실성 주 지표가 아님</H1>
    <Text>2026-11-18 구분: 아래 BPRS 제안은 증상 내용의 보조 평가에만 해당합니다. 발화 현실성은 PATIENTSIM Realism 등 직접 평가 문헌을 별도로 검토했습니다. 네 항목을 합산한 단축척도를 만들지 않습니다. 원기준 유지와 LLM 판독 검증은 별개의 문제입니다.</Text>
    <div style={{padding:16,borderLeft:`3px solid ${theme.accent.primary}`,background:theme.fill.tertiary}}>
      <Text weight="semibold">핵심 제한: 개념적 와해를 검증된 자동 주 지표로 확정하지 않는다</Text>
      <Text>BPRS 직접 연구에서 개념적 와해는 약한 항목이었습니다. 환각·망상 등 증상 내용과 사고형식을 분리합니다. 한국어 합성 면담에서 현재 평가자의 타당성은 아직 확인되지 않았습니다.</Text>
    </div>
    <H2>후보별 원기준 유지와 실행 조건</H2>
    <Table headers={["척도 / 항목","판정","유지할 점수·절차","현실적 제한"]} rows={evidence.candidates.map(s=>[<a key={s.id} href={s.source} target="_blank" rel="noreferrer" style={{color:theme.text.link}}>{s.name}</a>,s.decision,s.scoring,s.constraint])} />
    <Row align="center" justify="space-between" wrap>
      <H2>원문 확인 범위</H2>
      <Select value={selected} onChange={setSelected} options={evidence.candidates.map(s=>({value:s.id,label:s.name}))} />
    </Row>
    <Text weight="semibold">{current.name} · {current.scope}</Text>
    <Text>{current.preserve}</Text>
    <Text style={{color:theme.text.secondary}}>실제 검토: {current.source_read}</Text>
    <a href={current.source} target="_blank" rel="noreferrer" style={{color:theme.text.link}}>원문 열기</a>
    <Divider />
    <H2>BPRS 출발안에서 나오는 수치</H2>
    <Text>한 대화마다 9 의심, 10 환각, 11 비정상적 사고내용, 15 개념적 와해의 원평점 1~7을 기록합니다. 정보 부족은 NA입니다. 블록 평균이나 네 항목 총점을 계산하지 않습니다. 15번은 초기 탐색 지표입니다.</Text>
    <Text>비교 통계는 항목별 목표×관찰 혼동행렬, 정확한 목표 등급 일치, 과대·과소 판정입니다. 목표는 연구 사례의 설정이며 실제 환자 정답은 아닙니다. 점수가 높을수록 좋은 모듈이라는 뜻도 아닙니다.</Text>
    <H2>길이는 점수식을 바꿔 해결하지 않는다</H2>
    <Text>원 매뉴얼의 질문·분기 규칙과 필요한 평가 기간을 맞추고 전체 전사를 평정합니다. 증상 경험의 빈도와 대화 속 언급 횟수를 구분합니다. 생성 속도를 발화 시간으로 바꾸거나 원앵커를 1,000어절당 값으로 환산하지 않습니다.</Text>
    <Text>질문 기회를 맞춰도 관찰 발화량의 영향은 남습니다. 길이 분포·원점수와의 관계·NA율을 보고하고, 부족한 증거를 부재로 채우지 않습니다. 기술적 잘림도 기록합니다.</Text>
    <H2>직접 참고한 연구와 잘못 옮기면 안 되는 근거</H2>
    <Table headers={["연구","확인한 것","입증하지 않은 것"]} rows={evidence.critical_studies.map(s=>[<a key={s.name} href={s.url} target="_blank" rel="noreferrer" style={{color:theme.text.link}}>{s.name}</a>,s.finding,s.not_established])} />
    <Text style={{color:theme.text.secondary}}>BPRS 원 매뉴얼은 로컬에 원본으로 보존하고 SHA-256을 기록했습니다. K-PSYRATS는 임상 검증 초록만 확인했으며 정식 전체 양식은 아직 확보하지 못했습니다. 독립 채점 틀은 준비했지만 원문 기준 삽입과 현 평가자 점검 전 실행 완료로 간주하지 않습니다.</Text>
  </Stack>;
}
