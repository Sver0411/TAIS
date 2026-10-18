"""Render the two Markdown reports to A4 PDFs; no research computation.

Requires reportlab and Pillow. Set TAIS_JA_FONT to an embeddable Japanese
TrueType font if the macOS Arial Unicode font is unavailable. Original font
files are neither copied nor redistributed. Output stays in this portfolio.
"""
from pathlib import Path
import html
import os
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, LongTable, TableStyle
from PIL import Image as PILImage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPO = "https://github.com/Sver0411/TAIS/blob/docs/tais-research-portfolio/"
FALLBACK_SYMBOLS = set()


def fonts():
    jp = Path(os.environ.get("TAIS_JA_FONT", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"))
    if not jp.exists():
        raise FileNotFoundError("Set TAIS_JA_FONT to an embeddable Japanese TTF; no fallback tofu allowed")
    font = TTFont("Japanese", str(jp))
    required = set("農業環境信頼性適応検出考察概要")
    assert all(ord(c) in font.face.charToGlyph for c in required)
    pdfmetrics.registerFont(font)
    pdfmetrics.registerFontFamily("Japanese", normal="Japanese", bold="Japanese", italic="Japanese", boldItalic="Japanese")
    # ReportLab supplies Vera and VeraBd for reproducible Latin typography.
    import reportlab
    f = Path(reportlab.__file__).parent/"fonts"
    for name, filename in [("Latin","Vera.ttf"),("LatinBold","VeraBd.ttf"),("LatinItalic","VeraIt.ttf")]:
        pdfmetrics.registerFont(TTFont(name,str(f/filename)))
    pdfmetrics.registerFontFamily("Latin",normal="Latin",bold="LatinBold",italic="LatinItalic",boldItalic="LatinBold")
    for c in set((HERE/"TECHNICAL_REPORT_EN.md").read_text()):
        if ord(c)>127 and any(ord(c) not in pdfmetrics.getFont(n).face.charToGlyph
                              for n in ["Latin","LatinBold","LatinItalic"]):
            assert ord(c) in font.face.charToGlyph,c
            FALLBACK_SYMBOLS.add(c)


def target(url):
    if re.match(r"[a-z]+:",url): return url
    path, _, fragment=url.partition("#")
    dest=(HERE/path).resolve().relative_to(ROOT)
    return REPO+dest.as_posix()+("#"+fragment if fragment else "")


def inline(text):
    text=text.replace("\u2011","-").replace("\u2013","-").replace("\u2014","-")
    text=html.escape(text)
    for c in FALLBACK_SYMBOLS:
        text=text.replace(c,f'<font name="Japanese">{c}</font>')
    text=re.sub(r"\[([^\]]+)\]\(([^)]+)\)",lambda m:f'<link href="{html.escape(target(html.unescape(m[2])),quote=True)}" color="#225b83">{m[1]}</link>',text)
    text=re.sub(r"\*\*(.+?)\*\*",r"<b>\1</b>",text)
    text=re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)",r"<i>\1</i>",text)
    text=re.sub(r"`([^`]+)`",r'<font size="8.2">\1</font>',text)
    return text


def styles(japanese):
    family="Japanese" if japanese else "Latin"
    bold=family if japanese else "LatinBold"
    body=ParagraphStyle("body",fontName=family,fontSize=9.2 if japanese else 9.4,
                        leading=13.4 if japanese else 12.8,spaceAfter=5,
                        wordWrap="CJK" if japanese else None,
                        alignment=0 if japanese else TA_JUSTIFY,textColor=colors.HexColor("#202b33"))
    return {"body":body,
            "title":ParagraphStyle("title",parent=body,fontName=bold,fontSize=16 if japanese else 21,
                                   leading=23 if japanese else 26,spaceAfter=11,keepWithNext=True,textColor=colors.HexColor("#1f4259")),
            "h2":ParagraphStyle("h2",parent=body,fontName=bold,fontSize=11 if japanese else 12,
                                leading=16,spaceBefore=9,spaceAfter=5,keepWithNext=True,textColor=colors.HexColor("#1f4259")),
            "h3":ParagraphStyle("h3",parent=body,fontName=bold,fontSize=10,leading=14,spaceBefore=7,spaceAfter=4,keepWithNext=True),
            "deck":ParagraphStyle("deck",parent=body,fontSize=11,leading=15,spaceAfter=10,textColor=colors.HexColor("#526a77")),
            "caption":ParagraphStyle("caption",parent=body,fontSize=7.8 if japanese else 8,leading=10.7,spaceAfter=7),
            "cell":ParagraphStyle("cell",parent=body,fontSize=8.1 if japanese else 8.2,leading=11.2,spaceAfter=0,alignment=0),
            "headcell":ParagraphStyle("headcell",parent=body,fontName=bold,fontSize=8.1 if japanese else 8.2,leading=11.2,spaceAfter=0,alignment=0)}


class Report(SimpleDocTemplate):
    def afterFlowable(self, flow):
        if isinstance(flow,Paragraph) and flow.style.name in ["title","h2"]:
            title=flow.getPlainText(); key="section-"+str(self.seq.nextf("heading"))
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title,key,level=0,closed=False)


def render(name, japanese=False):
    s=styles(japanese); lines=(HERE/(name+".md")).read_text().splitlines()
    width=A4[0]-36*mm; story=[];i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line=="<!-- PAGEBREAK -->": story.append(PageBreak());i+=1;continue
        image=re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)",line)
        if image:
            path=HERE/image[2]
            with PILImage.open(path) as img: w,h=img.size
            story.append(Image(str(path),width=width,height=width*h/w));i+=1;continue
        if line.startswith("|"):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith("|"):
                row=[v.strip() for v in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[: -]+",v) for v in row): rows.append(row)
                i+=1
            n=len(rows[0]); lengths=[max(len(row[j]) for row in rows) for j in range(n)]
            weights=[max(10,min(65,v)) for v in lengths]
            if japanese and n==2:weights=[24,76]
            widths=[width*v/sum(weights) for v in weights]
            if not japanese and rows[0][0] in ["Stage","Multiplier"]:
                first=64 if rows[0][0]=="Multiplier" else 52
                widths=[first]+[(width-first)*v/sum(weights[1:]) for v in weights[1:]]
            data=[[Paragraph(inline(v),s["headcell"] if k==0 else s["cell"]) for v in row] for k,row in enumerate(rows)]
            table=LongTable(data,colWidths=widths,repeatRows=1,hAlign="LEFT")
            table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e9f0f5")),
                                       ("LINEBELOW",(0,0),(-1,0),.6,colors.HexColor("#587387")),
                                       ("LINEBELOW",(0,1),(-1,-1),.25,colors.HexColor("#c7d3dc")),
                                       ("VALIGN",(0,0),(-1,-1),"TOP"),
                                       ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
                                       ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
            story.extend([table,Spacer(1,6)]);continue
        heading=re.match(r"^(#{1,3}) (.+)",line)
        if heading:
            key={1:"title",2:"h2",3:"h3"}[len(heading[1])]
            if heading[2].startswith("Reproducible mechanisms"):key="deck"
            story.append(Paragraph(inline(heading[2]),s[key]))
            if heading[2]=="References" and not japanese:
                s["body"]=ParagraphStyle("reference",parent=s["body"],fontSize=8.5,leading=11.1,spaceAfter=5)
            i+=1;continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(("#","|","![","<!--")):
            paragraph.append(lines[i].strip());i+=1
        text=" ".join(paragraph)
        key="caption" if text.startswith(("Figure ","図A","図B","出典：")) else "body"
        story.append(Paragraph(inline(text),s[key]))
    title="農業IoTにおけるセンサ信頼性とイベント検出" if japanese else "TAIS: mechanisms, conditional benefits, and limits"
    def furniture(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor("#b7c7d2"));canvas.line(18*mm,16*mm,A4[0]-18*mm,16*mm)
        canvas.setFont("Latin",7.5);canvas.setFillColor(colors.HexColor("#526a77"))
        canvas.drawString(18*mm,11*mm,"TAIS | Research portfolio | Evidence: f21bc2f | 18 Oct 2026")
        canvas.drawRightString(A4[0]-18*mm,11*mm,str(doc.page));canvas.restoreState()
    doc=Report(str(HERE/(name+".pdf")),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,
               topMargin=17*mm,bottomMargin=22*mm,title=title,author="Sver0411",
               subject="Unpublished research portfolio; no new effectiveness experiment")
    doc.build(story,onFirstPage=furniture,onLaterPages=furniture)
    print("Rendered",name+".pdf")


if __name__=="__main__":
    fonts()
    render("RESEARCH_SUMMARY_JA",japanese=True)
    render("TECHNICAL_REPORT_EN")
