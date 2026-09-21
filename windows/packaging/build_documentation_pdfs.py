#!/usr/bin/env python3
"""Build the Windows 2.0 User Guide and What's New PDFs."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageTemplate,
    PageBreak,
    Paragraph,
    Spacer,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "user"
GUIDE_OUTPUT = SOURCE / "VisionEval-Workbench-2.0-Windows-User-Guide.pdf"
WHATS_NEW_OUTPUT = SOURCE / "VisionEval-Workbench-2.0-Whats-New-Windows.pdf"
GUIDE_PAGES = [
    "README.md", "setup.md", "getting-started.md", "core-concepts.md", "explore.md",
    "create-and-review.md", "run.md", "compare.md", "hypercube.md",
    "settings-workspaces-storage.md", "data-units-provenance.md", "troubleshooting.md",
    "keyboard-shortcuts.md", "future-improvements.md",
]


class GuideDocument(BaseDocTemplate):
    def __init__(self, filename: Path, title: str):
        super().__init__(
            str(filename), pagesize=letter, title=title, author="VisionEval Workbench",
            leftMargin=0.72 * inch, rightMargin=0.72 * inch,
            topMargin=0.72 * inch, bottomMargin=0.68 * inch,
        )
        self.guide_title = title
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=self._decorate))

    def _decorate(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D7DEE8"))
        canvas.setLineWidth(0.5)
        canvas.line(self.leftMargin, 0.53 * inch, letter[0] - self.rightMargin, 0.53 * inch)
        canvas.setFillColor(colors.HexColor("#526173"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(self.leftMargin, 0.34 * inch, "VisionEval Workbench 2.0 - Windows x64")
        canvas.drawRightString(letter[0] - self.rightMargin, 0.34 * inch, f"Page {doc.page}")
        canvas.restoreState()


def inline_markup(value: str) -> str:
    value = html.escape(value.strip())
    value = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    return value


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=25,
                                leading=30, textColor=colors.HexColor("#17365D"), alignment=TA_LEFT,
                                spaceAfter=16),
        "subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontSize=12, leading=17,
                                   textColor=colors.HexColor("#526173"), spaceAfter=24),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=18,
                             leading=22, textColor=colors.HexColor("#17365D"), spaceBefore=12, spaceAfter=8),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=14,
                             leading=18, textColor=colors.HexColor("#245B88"), spaceBefore=10, spaceAfter=6),
        "h3": ParagraphStyle("H3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=11.5,
                             leading=15, textColor=colors.HexColor("#2E526D"), spaceBefore=7, spaceAfter=4),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.5,
                               leading=13.5, textColor=colors.HexColor("#1F2933"), spaceAfter=6),
        "bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName="Helvetica", fontSize=9.3,
                                 leading=13, leftIndent=3, textColor=colors.HexColor("#1F2933")),
        "code": ParagraphStyle("Code", parent=base["Code"], fontName="Courier", fontSize=7.8,
                               leading=10.5, leftIndent=8, rightIndent=8, borderColor=colors.HexColor("#D7DEE8"),
                               borderWidth=0.5, borderPadding=6, backColor=colors.HexColor("#F5F7FA"), spaceAfter=7),
        "toc": ParagraphStyle("TOC", parent=base["BodyText"], fontSize=10, leading=15,
                              textColor=colors.HexColor("#245B88"), leftIndent=10),
    }


def markdown_flowables(text: str, style_map: dict, *, drop_first_title: bool = False):
    story, paragraph, bullets, code = [], [], [], []
    in_code = False

    def flush_paragraph():
        if paragraph:
            story.append(Paragraph(inline_markup(" ".join(paragraph)), style_map["body"]))
            paragraph.clear()

    def flush_bullets():
        if bullets:
            items = [ListItem(Paragraph(inline_markup(item), style_map["bullet"]), leftIndent=12) for item in bullets]
            story.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=16, bulletFontSize=6))
            story.append(Spacer(1, 4))
            bullets.clear()

    def flush_code():
        if code:
            story.append(Paragraph("<br/>".join(html.escape(line).replace(" ", "&nbsp;") for line in code), style_map["code"]))
            code.clear()

    first_heading = True
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            flush_paragraph(); flush_bullets()
            if in_code: flush_code()
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
            continue
        match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if match:
            flush_paragraph(); flush_bullets()
            if first_heading and drop_first_title:
                first_heading = False
                continue
            first_heading = False
            story.append(Paragraph(inline_markup(match.group(2)), style_map[f"h{len(match.group(1))}"]))
        elif re.match(r"^[-*]\s+", line):
            flush_paragraph(); bullets.append(re.sub(r"^[-*]\s+", "", line))
        elif re.match(r"^\d+\.\s+", line):
            flush_paragraph(); bullets.append(re.sub(r"^\d+\.\s+", "", line))
        elif not line.strip() or line.strip() == "---":
            flush_paragraph(); flush_bullets()
        elif line.lstrip().startswith("!["):
            continue
        else:
            paragraph.append(line.strip())
    flush_paragraph(); flush_bullets(); flush_code()
    return story


def build_guide(output: Path):
    s = styles()
    story = [
        Spacer(1, 0.35 * inch),
        Paragraph("VisionEval Workbench 2.0", s["title"]),
        Paragraph("Windows x64 User Guide", ParagraphStyle("Cover", parent=s["h1"], fontSize=20, leading=24)),
        Spacer(1, 0.15 * inch),
        Paragraph("Native VisionEval execution, Standard projects, Hypercube workflows, analysis, export, recovery, and troubleshooting.", s["subtitle"]),
        Paragraph("Release candidate - UNSIGNED", ParagraphStyle("Unsigned", parent=s["body"], textColor=colors.HexColor("#9B3A22"), fontName="Helvetica-Bold")),
        Spacer(1, 0.45 * inch),
        Paragraph("Contents", s["h1"]),
    ]
    for name in GUIDE_PAGES:
        source = (SOURCE / name).read_text(encoding="utf-8")
        heading = next((line.removeprefix("# ") for line in source.splitlines() if line.startswith("# ")), name)
        story.append(Paragraph(inline_markup(heading), s["toc"]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("Windows executes all Standard and Hypercube runs through one shared FIFO native-runtime slot. Docker is neither required nor included.", s["body"]))
    story.append(PageBreak())
    for name in GUIDE_PAGES:
        story.append(Spacer(1, 12))
        story.extend(markdown_flowables((SOURCE / name).read_text(encoding="utf-8"), s))
    GuideDocument(output, "VisionEval Workbench 2.0 Windows User Guide").build(story)


def build_whats_new(output: Path):
    s = styles()
    story = [
        Spacer(1, 0.4 * inch),
        Paragraph("What's New in VisionEval Workbench 2.0", s["title"]),
        Paragraph("Windows x64 - native runtime edition", s["subtitle"]),
    ]
    story.extend(markdown_flowables((SOURCE / "whats-new.md").read_text(encoding="utf-8"), s, drop_first_title=True))
    GuideDocument(output, "What's New in VisionEval Workbench 2.0 for Windows").build(story)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        build_guide(GUIDE_OUTPUT)
        build_whats_new(WHATS_NEW_OUTPUT)
    counts = {GUIDE_OUTPUT.name: len(PdfReader(GUIDE_OUTPUT).pages), WHATS_NEW_OUTPUT.name: len(PdfReader(WHATS_NEW_OUTPUT).pages)}
    if any(value < 1 for value in counts.values()):
        raise SystemExit("Documentation PDF has no pages")
    manifest_path = SOURCE / "documentation.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = {item["filename"]: item["pageCount"] for item in manifest["documents"]}
    if args.check and actual != counts:
        raise SystemExit(f"Documentation manifest page counts are stale: expected {counts}, found {actual}")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
