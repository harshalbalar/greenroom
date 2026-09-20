"""
Resume templates — 3 built-in styles for DOCX generation.

Each template takes the same structured sections (parsed from Gemini's
Markdown output) and formats them with different visual styles.

Templates:
    1. Classic — conservative, serif font, traditional layout (banking, law, enterprise)
    2. Modern — clean sans-serif, color accents, section dividers (tech, startups)
    3. Minimal — maximum whitespace, ultra-clean, no borders (design, creative)
"""

import re
import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


# ── Parse Markdown into sections ──────────────────────────────────────

def parse_resume_markdown(markdown: str) -> dict:
    """Parse Gemini's Markdown resume into structured sections."""
    sections = {
        "name": "",
        "subtitle": "",
        "contact": "",
        "tagline": "",
        "sections": [],  # list of {"heading": str, "content": [str or {"bullet": str}]}
    }

    lines = markdown.strip().split('\n')
    current_section = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # H1: Name
        if stripped.startswith('# ') and not stripped.startswith('##'):
            sections["name"] = stripped.lstrip('# ').strip()
            continue

        # Bold subtitle: **Title**
        if stripped.startswith('**') and stripped.endswith('**') and stripped.count('**') == 2 and not current_section:
            sections["subtitle"] = stripped.strip('* ').strip()
            continue

        # Contact line with pipes
        if '|' in stripped and len(stripped.split('|')) >= 3 and not current_section:
            clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', stripped)
            sections["contact"] = clean.strip()
            continue

        # Italic tagline
        if stripped.startswith('*') and stripped.endswith('*') and not stripped.startswith('**') and not current_section:
            sections["tagline"] = stripped.strip('* ').strip()
            continue

        # Section heading (H2 or H3)
        if stripped.startswith('#'):
            heading = stripped.lstrip('#').strip().rstrip(':')
            current_section = {"heading": heading, "content": []}
            sections["sections"].append(current_section)
            continue

        # Horizontal rule
        if stripped in ('---', '***', '___'):
            continue

        # Bullet point
        if re.match(r'^[\*\-•]\s', stripped):
            clean = re.sub(r'^[\*\-•]\s+', '', stripped)
            if current_section is not None:
                current_section["content"].append({"bullet": clean})
            continue

        # Regular text
        if current_section is not None:
            current_section["content"].append(stripped)
        elif not sections["name"]:
            sections["name"] = stripped

    return sections


def _add_inline_formatting(paragraph, text):
    """Parse inline bold/italic Markdown into Word runs."""
    pattern = r'(\*\*(.+?)\*\*|\*(.+?)\*|\[(.+?)\]\((.+?)\)|([^*\[\]]+))'
    for match in re.finditer(pattern, text):
        if match.group(2):
            run = paragraph.add_run(match.group(2))
            run.bold = True
        elif match.group(3):
            run = paragraph.add_run(match.group(3))
            run.italic = True
        elif match.group(4):
            paragraph.add_run(match.group(4))
        elif match.group(6):
            paragraph.add_run(match.group(6))


# ── Template 1: Classic ───────────────────────────────────────────────

def build_classic(sections: dict) -> io.BytesIO:
    """Conservative, traditional layout. Georgia/Times font, no color.
    Best for: banking, law, consulting, government, enterprise."""

    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(0.7)
        s.bottom_margin = Inches(0.7)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)

    style = doc.styles['Normal']
    style.font.name = 'Georgia'
    style.font.size = Pt(10.5)
    style.font.color.rgb = RGBColor(30, 30, 30)
    style.paragraph_format.space_after = Pt(2)
    style.paragraph_format.line_spacing = Pt(13)

    # Name
    if sections["name"]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(sections["name"])
        run.bold = True
        run.font.size = Pt(18)
        run.font.name = 'Georgia'

    # Subtitle
    if sections["subtitle"]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(sections["subtitle"])
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(80, 80, 80)

    # Contact
    if sections["contact"]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(sections["contact"])
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(100, 100, 100)

    # Tagline
    if sections["tagline"]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(sections["tagline"])
        run.italic = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(100, 100, 100)

    # Sections
    for sec in sections["sections"]:
        # Heading with double bottom border (classic style)
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(sec["heading"].upper())
        run.bold = True
        run.font.size = Pt(10.5)
        run.font.name = 'Georgia'
        run.font.color.rgb = RGBColor(0, 0, 0)

        # Double border
        pPr = p._element.get_or_add_pPr()
        pBdr = pPr.makeelement(qn('w:pBdr'), {})
        bottom = pBdr.makeelement(qn('w:bottom'), {
            qn('w:val'): 'double', qn('w:sz'): '4',
            qn('w:space'): '1', qn('w:color'): '333333',
        })
        pBdr.append(bottom)
        pPr.append(pBdr)

        # Content
        for item in sec["content"]:
            if isinstance(item, dict) and "bullet" in item:
                p = doc.add_paragraph(style='List Bullet')
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.left_indent = Inches(0.3)
                _add_inline_formatting(p, item["bullet"])
                for run in p.runs:
                    run.font.size = Pt(10.5)
                    run.font.name = 'Georgia'
            else:
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(2)
                _add_inline_formatting(p, item)
                for run in p.runs:
                    run.font.size = Pt(10.5)
                    run.font.name = 'Georgia'

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ── Template 2: Modern ────────────────────────────────────────────────

def build_modern(sections: dict) -> io.BytesIO:
    """Clean, contemporary layout. Calibri, subtle blue accents, thin dividers.
    Best for: tech, startups, engineering, product roles."""

    ACCENT = RGBColor(59, 89, 152)  # professional blue

    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(0.5)
        s.bottom_margin = Inches(0.5)
        s.left_margin = Inches(0.65)
        s.right_margin = Inches(0.65)

    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(10)
    style.font.color.rgb = RGBColor(33, 33, 33)
    style.paragraph_format.space_after = Pt(1)
    style.paragraph_format.line_spacing = Pt(13)

    # Name
    if sections["name"]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(sections["name"])
        run.bold = True
        run.font.size = Pt(20)
        run.font.color.rgb = ACCENT

    # Subtitle
    if sections["subtitle"]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(sections["subtitle"])
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(80, 80, 80)

    # Contact
    if sections["contact"]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(sections["contact"])
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(100, 100, 100)

    # Tagline
    if sections["tagline"]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run(sections["tagline"])
        run.italic = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(120, 120, 120)

    # Sections
    for sec in sections["sections"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(sec["heading"].upper())
        run.bold = True
        run.font.size = Pt(10.5)
        run.font.color.rgb = ACCENT

        # Thin colored bottom border
        pPr = p._element.get_or_add_pPr()
        pBdr = pPr.makeelement(qn('w:pBdr'), {})
        bottom = pBdr.makeelement(qn('w:bottom'), {
            qn('w:val'): 'single', qn('w:sz'): '4',
            qn('w:space'): '1', qn('w:color'): '3B5998',
        })
        pBdr.append(bottom)
        pPr.append(pBdr)

        for item in sec["content"]:
            if isinstance(item, dict) and "bullet" in item:
                p = doc.add_paragraph(style='List Bullet')
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.left_indent = Inches(0.25)
                _add_inline_formatting(p, item["bullet"])
                for run in p.runs:
                    run.font.size = Pt(10)
                    run.font.name = 'Calibri'
            else:
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(2)
                _add_inline_formatting(p, item)
                for run in p.runs:
                    run.font.size = Pt(10)
                    run.font.name = 'Calibri'

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ── Template 3: Minimal ──────────────────────────────────────────────

def build_minimal(sections: dict) -> io.BytesIO:
    """Ultra-clean, lots of whitespace. Helvetica-style, no borders.
    Best for: design, creative, marketing, consulting."""

    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.9)
        s.right_margin = Inches(0.9)

    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)
    style.font.color.rgb = RGBColor(50, 50, 50)
    style.paragraph_format.space_after = Pt(2)
    style.paragraph_format.line_spacing = Pt(14)

    # Name — left-aligned, large
    if sections["name"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(sections["name"])
        run.bold = True
        run.font.size = Pt(22)
        run.font.color.rgb = RGBColor(30, 30, 30)
        run.font.name = 'Arial'

    # Subtitle — left-aligned, light
    if sections["subtitle"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(sections["subtitle"])
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(120, 120, 120)

    # Contact — left-aligned, small
    if sections["contact"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(sections["contact"])
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(140, 140, 140)

    # Tagline
    if sections["tagline"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(12)
        run = p.add_run(sections["tagline"])
        run.italic = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(140, 140, 140)

    # Sections — no borders, just spacing and caps
    for sec in sections["sections"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(sec["heading"].upper())
        run.bold = False
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(140, 140, 140)
        run.font.name = 'Arial'
        # Letter spacing effect via character spacing
        run.font.letter_spacing = Pt(1.5)

        for item in sec["content"]:
            if isinstance(item, dict) and "bullet" in item:
                # Minimal bullets: just a dash, no indent
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.left_indent = Inches(0.15)
                run = p.add_run("–  ")
                run.font.color.rgb = RGBColor(180, 180, 180)
                run.font.size = Pt(10)
                _add_inline_formatting(p, item["bullet"])
                for r in p.runs[1:]:
                    r.font.size = Pt(10)
                    r.font.name = 'Arial'
            else:
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(3)
                _add_inline_formatting(p, item)
                for run in p.runs:
                    run.font.size = Pt(10)
                    run.font.name = 'Arial'

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ── Template registry ─────────────────────────────────────────────────

TEMPLATES = {
    "classic": {"name": "Classic", "desc": "Traditional, serif font, double borders — banking, law, enterprise", "builder": build_classic},
    "modern": {"name": "Modern", "desc": "Clean Calibri, blue accents, thin dividers — tech, startups", "builder": build_modern},
    "minimal": {"name": "Minimal", "desc": "Ultra-clean, lots of whitespace, no borders — design, creative", "builder": build_minimal},
    "user_template": {"name": "My Template", "desc": "Your original DOCX format with tailored content", "builder": None},  # handled separately
}


def build_resume_from_template(markdown: str, template: str = "modern", original_file: bytes | None = None) -> io.BytesIO:
    """Parse Markdown resume and build DOCX using the selected template.

    Args:
        markdown: Gemini's tailored resume in Markdown format
        template: Template ID ('classic', 'modern', 'minimal', or 'user_template')
        original_file: Raw DOCX bytes for user_template mode. Required when template='user_template'.
    """
    if template == "user_template":
        if not original_file:
            # Fallback to modern if no original file available
            template = "modern"
        else:
            from user_template import build_user_template
            return build_user_template(markdown, original_file)

    sections = parse_resume_markdown(markdown)
    builder = TEMPLATES.get(template, TEMPLATES["modern"])["builder"]
    return builder(sections)
