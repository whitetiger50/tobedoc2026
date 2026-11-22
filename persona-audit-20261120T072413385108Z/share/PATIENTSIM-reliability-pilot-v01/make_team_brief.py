"""One-page visual explanation: problem -> criterion -> judge pilot -> prompt use."""
from pathlib import Path
import hashlib
import json
import subprocess
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader
from native_pdf_canvas import NativeCanvas

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = REPO/'output'/'pdf'
PDF = OUT/'조현병_발화평가_파일럿_팀공유_1장.pdf'


def main():
    spec=json.loads((ROOT/'pilot-design.json').read_text())
    assert spec['counts']['total_dialogues']==48 and spec['counts']['planned_judgments']==720
    OUT.mkdir(parents=True,exist_ok=True)
    W,H=A4
    M=36
    CW=W-2*M
    navy=colors.HexColor('#142F42')
    ink=colors.HexColor('#1F303B')
    muted=colors.HexColor('#536774')
    teal=colors.HexColor('#126A70')
    pale=colors.HexColor('#EEF5F5')
    line=colors.HexColor('#CBD8DD')
    white=colors.white
    c=NativeCanvas(str(PDF),pagesize=A4)
    c.setTitle('환자처럼 말하는지, 프롬프트를 어떻게 비교할까?')
    c.setAuthor('투비닥터 연구팀')
    c.setSubject('문제의식부터 프롬프트 개선·최종 비교까지, 팀 설명용 개정 요약')
    bounds=[]

    def text(txt,x,top,w=CW,size=10.5,leading=15,color=ink,max_h=None):
        c.paragraph(txt,x,top,w,size,leading,color,max_h)

    def strong(txt,x,baseline,size,color):
        c.strong(txt,x,baseline,size,color)

    def section(number,title,top):
        strong(number,M,top-13,11.2,teal)
        strong(title,M+30,top-13,13.1,navy)

    def arrow(x,y,length=14):
        c.setStrokeColor(teal)
        c.setLineWidth(1.2)
        c.line(x,y,x+length,y)
        c.line(x+length,y,x+length-4,y+3)
        c.line(x+length,y,x+length-4,y-3)

    # Explain the provenance and construction of all 48 planned dialogues.
    c.setFillColor(navy)
    c.rect(0,H-108,W,108,fill=1,stroke=0)
    text('투비닥터 연구팀  /  팀 설명용 개정판  /  2026.11.18',M,H-13,size=8.1,
         leading=11,color=colors.HexColor('#C4D6DF'))
    strong('환자처럼 말하는지,',M,H-51,21,white)
    strong('프롬프트를 어떻게 비교할까?',M,H-79,21,white)
    text('평가자를 먼저 시험하고, 통과한 채점 방식으로 개선 효과를 비교한다.',M,H-90,
         size=9.5,leading=13,color=colors.HexColor('#E4EEF2'))

    section('01','출발점: 좋은 발화를 가려낼 기준이 필요하다',H-123)
    text('실제 환자 발화와 전문의 평가가 부족해, 우리 프롬프트가 더 현실적인지 확인하기 어렵다.<br/>증상을 설명하는 답변과, 환자 입장에서 질문에 반응하는 대화를 구분해야 한다.',
         M,H-147,size=10.3,leading=15,max_h=32)

    section('02','평가 기준: 이 환자가 이렇게 답할 법한가?',H-190)
    text('PATIENTSIM의 <font color="#126A70">전체 대화 현실성 1~4점</font>을 쓴다.[1] 공개 채점표와 임상의 비교 선례가 있어<br/>출발점으로 선택했다. 짧은 답변·탈선 자체보다 환자 설정과 앞뒤 문맥에 맞는지를 본다.',
         M,H-214,size=10.1,leading=14.8,max_h=32)

    section('03','준비할 자료: 환자 설정 12개 → 면담 24개 → 변형 24개',H-257)
    text('<font color="#126A70">12개 사례 = Codex(LLM)가 이번 파일럿을 위해 작성한 가상 환자 프로필 초안.</font><br/>나이·생활 배경·증상·말하는 방식을 정한 설정이며, 실제 환자에서 수집한 사례가 아니다.',
         M,H-281,size=9.3,leading=13.3,max_h=28)
    case_lines=[
        '① 환청·망상은 있으나 말은 정돈됨: 22세 대학생 / 34세 사무직 / 45세 소매점 운영자',
        '② 사고 흐름의 어려움: 26세 대학원 휴학생 / 31세 물류 업무 휴직자 / 39세 프리랜서',
        '③ 자발적 발화가 적음: 28세 구직자 / 51세 세탁 업무 종사자 / 36세 음식점 휴직자',
        '④ 안정적이고 병식이 보존됨: 24세 복학생 / 47세 약국 업무 경험자 / 58세 은퇴 도서관 직원',
    ]
    text('<br/>'.join(case_lines),M,H-313,size=8.8,leading=12.3,color=muted,max_h=51)
    text('<font color="#126A70">면담 24개:</font> 같은 생성 LLM으로 각 프로필에 기존 페르소나·우리 프롬프트를 각각 적용한다.<br/>즉, 프로필 12개 × 프롬프트 2개 = 면담 24개이며, 면담 하나는 동일 질문 12개의 문답이다.',
         M,H-367,size=9.2,leading=13,max_h=28)
    text('<font color="#126A70">변형 24개:</font> 위 면담을 하나씩 바꾼 추가 대화다. 12개는 보고서식 설명·반복·문맥 오류를 넣고,<br/>나머지 12개는 의미·말투를 유지한 채 길이만 바꾼다. 새로운 환자 24명을 만드는 것이 아니다.',
         M,H-396,size=9.2,leading=13,max_h=28)

    section('04','채점자 검사: 같은 48개 대화를 세 모델이 독립 판독한다',H-432)
    strong('GPT-6.1 Sol  +  Claude Opus 5.5  +  Gemini 4 Argon',M,H-467,10.4,navy)
    text('각 대화를 모델별로 새 문맥에서 5회 채점한다. 생성 조건과 다른 평가자의 점수는 숨긴다.[2]',
         M,H-473,size=9.3,leading=13.5,max_h=15)

    gap=10
    col=(CW-3*gap)/4
    top=H-495
    checks=[
        ('반복 일관성','다시 읽어도\n비슷한 점수인가?','같은 모델의 5회 점수를 비교'),
        ('평가자 간 일치','다른 모델도\n비슷하게 보는가?','세 모델의 대표 점수를 비교'),
        ('오류 감지','답변을 뒤섞으면\n점수를 낮추는가?','보고서식·반복·문맥 오류'),
        ('길이에 의한 편향','같은 답을 늘려 쓰면\n점수가 달라지는가?','의미·말투 유지, 분량만 변경'),
    ]
    for k,(label,question,detail) in enumerate(checks):
        x=M+k*(col+gap)
        c.setFillColor(pale)
        c.rect(x,top-77,col,77,fill=1,stroke=0)
        text(label,x+9,top-7,w=col-18,size=8.7,leading=12,color=teal,max_h=13)
        text(question.replace('\n','<br/>'),x+9,top-24,w=col-18,size=9.9,leading=14,color=navy,max_h=30)
        text(detail,x+9,top-62,w=col-18,size=6.8,leading=10,color=muted,max_h=11)
    text('통합: 모델별 5회 중앙값 → 세 모델 중앙값의 중앙값. 총 48개 × 3종 × 5회 = 720개 판독.',
         M,H-580,size=9.0,leading=13,color=teal,max_h=15)

    section('05','통과 후: 프롬프트를 고치고, 새 사례로 비교한다',H-606)
    top=H-632
    bw=(CW-3*20)/4
    labels=[('같은 새 사례','같은 생성 모델·질문'),('두 프롬프트','기존 vs. 개선'),('검증된 채점 방식','조건을 숨기고 평가'),('결과 비교','여러 사례의 점수 분포')]
    for k,(label,sub) in enumerate(labels):
        x=M+k*(bw+20)
        c.setStrokeColor(line)
        c.setFillColor(white)
        c.setLineWidth(.7)
        c.rect(x,top-39,bw,39,fill=1,stroke=1)
        text(label,x+7,top-6,w=bw-14,size=9.3,leading=12,color=navy,max_h=13)
        text(sub,x+7,top-23,w=bw-14,size=7.3,leading=10.5,color=muted,max_h=12)
        if k<3: arrow(x+bw+3,top-20,14)
    text('개발 중에는 낮은 점수의 대화와 이유를 보고 수정한다. 최종 비교는 수정에 쓰지 않은 새 사례에서<br/>같은 생성 모델·질문·채점 방식으로 한다. 한두 개의 좋은 예보다 여러 사례의 개선을 확인한다.',
         M,H-680,size=9.5,leading=14,max_h=30)

    c.setFillColor(navy)
    c.rect(M,H-761,CW,41,fill=1,stroke=0)
    text('먼저 채점자의 일관성과 오류 구분 능력이 사전 기준을 통과하는지 확인한다.',
         M+10,H-726,w=CW-20,size=9.5,leading=13,color=white,max_h=15)
    text('세 모델의 합의가 임상 타당성을 보장하지는 않는다. 전문의의 맹검 평가는 후속 검증으로 추가한다.',
         M+10,H-744,w=CW-20,size=8.1,leading=11.5,color=colors.HexColor('#DFEBF0'),max_h=13)

    refs=[
        ('[1] PATIENTSIM, NeurIPS 2025. 공개 현실성 평가 기준·임상의 비교.',
         'https://proceedings.neurips.cc/paper_files/paper/2025/file/24945e3bdc7b3f4b2e64b9979a16f38e-Paper-Datasets_and_Benchmarks_Track.pdf'),
        ('[2] Stadler 등, JMIR Medical Education 2026;12:e94666. 동일 입력 5회 반복 채점.',
         'https://mededu.jmir.org/2026/1/e94666/'),
    ]
    for k,(label,url) in enumerate(refs):
        text(f'<link href="{escape(url)}" color="#536774">{escape(label)}</link>',
             M,H-772-k*12.5,size=7.4,leading=10.5,color=muted,max_h=12)
    c.showPage()
    c.save()

    reader=PdfReader(PDF)
    assert len(reader.pages)==1
    # Poppler supports the native PDF's Adobe-Korea1 CID character mapping.
    content=subprocess.check_output(['/opt/homebrew/bin/pdftotext',str(PDF),'-'],text=True)
    for expected in ['GPT-6.1 Sol','Claude Opus 5.5','Gemini 4 Argon','PATIENTSIM','720','새 사례','중앙값','Codex','실제 환자에서 수집한 사례가 아니다','면담 24개','변형 24개']:
        assert expected in content,expected
    for removed in ['응급실용 기준을 정신과 맥락에 적용한','설계 v0.2','계획 요약이며 실험 결과가 아님','판별력·길이 영향']:
        assert removed not in content,removed
    assert len(reader.pages[0]['/Annots'].get_object())==2
    embedded=False
    font_names=set()
    def inspect_font(ref):
        nonlocal embedded
        f=ref.get_object()
        font_names.add(str(f.get('/BaseFont','')))
        if f.get('/FontDescriptor'):
            desc=f['/FontDescriptor'].get_object()
            embedded=embedded or any(k in desc for k in ['/FontFile','/FontFile2','/FontFile3'])
        descendants=f.get('/DescendantFonts')
        if descendants:
            for descendant in descendants.get_object():
                inspect_font(descendant)
    for ref in reader.pages[0]['/Resources']['/Font'].values():
        inspect_font(ref)
    assert embedded
    assert all('AppleSDGothicNeo' in n for n in font_names),font_names
    assert any('Regular' in n for n in font_names) and any('Bold' in n for n in font_names)
    review={'pdf':str(PDF),'pages':1,'sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),
            'font_embedded':embedded,'font_family':'Apple SD Gothic Neo','embedded_font_names':sorted(font_names),'source_links':2,'content_blocks':bounds,
            'communication_revision':'problem -> criterion and intent -> judge pilot -> future prompting workflow',
            'protocol_parameters_changed':False,'status':'text/layout bounds checked; visual review pending'}
    (ROOT/'team-brief-check.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in review.items() if k!='content_blocks'},ensure_ascii=False))

if __name__=='__main__':
    main()
