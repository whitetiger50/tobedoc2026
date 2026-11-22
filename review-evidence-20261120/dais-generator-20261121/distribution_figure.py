"""Draw a shareable vector figure using aggregate counts only."""
import json
from pathlib import Path
from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas

HERE = Path(__file__).resolve().parent
ARMS = {"patient":"Patient", "developed":"Developed", "base":"Role-only", "short":"Brief / vague"}
CATEGORIES = {
    "expanded":("Expanded", "#175969"), "direct":("Direct", "#93C5C1"),
    "clarification":("Clarification", "#D7834B"), "other":("Other", "#785C82"),
    "ambiguous":("Unresolved", "#B6A97F"), "technical_missing":("Missing", "#D6D8D6")}
DARK = HexColor("#1D3033")


def main():
    data = json.loads((HERE/"analysis.json").read_text())["readers"]
    canvas = Canvas(str(HERE/"first-reply-distributions.pdf"), pagesize=(830,530))
    canvas.setTitle("DAIS-C first-reply distributions by question and blinded reader")
    def text(x,y,content,size=10,bold=False):
        canvas.setFillColor(DARK)
        canvas.setFont("Helvetica-Bold" if bold else "Helvetica",size)
        canvas.drawString(x,y,content)
    text(33,489,"First replies to the DAIS-C interview questions",23,True)
    text(33,469,"Observed response types by source and blinded reader",13)
    active = [k for k in CATEGORIES if any(
        d["observed_counts"][k] for model in data.values() for q in model["questions"].values()
        for d in q["distribution"].values())]
    for qi,question in enumerate(("Q2","Q3")):
        for mi,(reader,title) in enumerate((("opus","Opus 5.5"),("gpt","GPT-6.1 Sol"))):
            x=33+mi*398; top=418-qi*155
            text(x,top,f"{question}  /  {title}",13,True)
            dist=data[reader]["questions"][question]["distribution"]
            for ai,(arm,arm_label) in enumerate(ARMS.items()):
                y=top-23-ai*21
                text(x,y,arm_label)
                xx=x+77; n=dist[arm]["N"]; bar_width=290
                for cat,(label,color) in CATEGORIES.items():
                    count=dist[arm]["observed_counts"][cat]
                    if not count:continue
                    w=bar_width*count/n
                    canvas.setFillColor(HexColor(color));canvas.rect(xx,y-3,w,15,fill=1,stroke=0)
                    canvas.setFillColor(HexColor("#FFFFFF") if cat in {"expanded","other"} else DARK)
                    canvas.setFont("Helvetica",8)
                    canvas.drawCentredString(xx+w/2,y+0.5,str(count))
                    xx+=w
            text(x+77,top-102,"0%",8);text(x+345,top-102,"100%",8)
    left=33
    for cat in active:
        label,color=CATEGORIES[cat]
        canvas.setFillColor(HexColor(color));canvas.rect(left,112,10,10,fill=1,stroke=0)
        text(left+15,113,label);left+=canvas.stringWidth(label,"Helvetica",10)+33
    text(33,86,"Bar widths show within-source percentages. Segment labels show counts.",10)
    text(33,69,"Each question has 7 patient replies and 21 replies per model condition (3 per interview input).",10)
    text(33,42,"Patient source: Delgaram-Nejad et al. (2023), UK Data Service, doi:10.5255/UKDA-SN-855021, CC BY-SA 4.0.",9)
    canvas.showPage();canvas.save()


if __name__=="__main__":
    main()
