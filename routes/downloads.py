"""Download routes — generate ATS-friendly Word docs from application data.

The tailored resume comes from Gemini as Markdown text. This module
parses that Markdown and renders it into properly formatted Word
documents with real bold, italic, headings, bullets, and links.
"""

import io
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from docx.shared import Pt, Inches, RGBColor
from database import get_db, User, Application, Job
from auth_core import get_current_user

router = APIRouter(prefix="/api/applications", tags=["downloads"])


# ── Markdown → docx helpers ──────────────────────────────────────────

def _add_formatted_runs(paragraph, text):
    """Parse inline Markdown (bold, italic, links) into Word runs."""
    # Pattern: **bold**, *italic*, [text](url), plain text
    pattern = r'(\*\*(.+?)\*\*|\*(.+?)\*|\[(.+?)\]\((.+?)\)|([^*\[\]]+))'

    for match in re.finditer(pattern, text):
        full = match.group(0)

        if match.group(2):  # **bold**
            run = paragraph.add_run(match.group(2))
            run.bold = True
        elif match.group(3):  # *italic*
            run = paragraph.add_run(match.group(3))
            run.italic = True
        elif match.group(4) and match.group(5):  # [text](url)
            run = paragraph.add_run(match.group(4))
            run.font.color.rgb = RGBColor(0, 0, 238)
        elif match.group(6):  # plain text
            paragraph.add_run(match.group(6))


def _build_resume_docx(tailored_resume: str) -> io.BytesIO:
    """Build an ATS-friendly resume Word doc from Markdown text."""
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn

    doc = Document()

    # Narrow margins
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.65)
        section.right_margin = Inches(0.65)

    # Base style
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(10)
    style.font.color.rgb = RGBColor(33, 33, 33)
    style.paragraph_format.space_after = Pt(1)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.line_spacing = Pt(13)

    lines = tailored_resume.strip().split('\n')
    is_first_heading = True

    for line in lines:
        stripped = line.strip()

        # Skip empty lines (add small spacing)
        if not stripped:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            pf = p.paragraph_format
            pf.space_after = Pt(2)
            continue

        # H1: # Name → large centered name
        if stripped.startswith('# ') and not stripped.startswith('##'):
            name = stripped.lstrip('# ').strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(0)
            run = p.add_run(name)
            run.bold = True
            run.font.size = Pt(18)
            run.font.color.rgb = RGBColor(0, 0, 0)
            continue

        # H2 or H3: ## Section / ### Section → section header with bottom border
        if stripped.startswith('#'):
            heading_text = stripped.lstrip('#').strip()
            # Remove trailing colons and clean up
            heading_text = heading_text.rstrip(':')

            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10) if not is_first_heading else Pt(4)
            p.paragraph_format.space_after = Pt(3)
            is_first_heading = False

            run = p.add_run(heading_text.upper())
            run.bold = True
            run.font.size = Pt(10.5)
            run.font.color.rgb = RGBColor(0, 0, 0)

            # Bottom border for section separation
            pPr = p._element.get_or_add_pPr()
            pBdr = pPr.makeelement(qn('w:pBdr'), {})
            bottom = pBdr.makeelement(qn('w:bottom'), {
                qn('w:val'): 'single',
                qn('w:sz'): '4',
                qn('w:space'): '1',
                qn('w:color'): '444444',
            })
            pBdr.append(bottom)
            pPr.append(pBdr)
            continue

        # Horizontal rule: --- or ***
        if stripped in ('---', '***', '___'):
            continue  # skip, section headers already have borders

        # Bullet: * item or - item
        if re.match(r'^[\*\-•]\s', stripped):
            clean = re.sub(r'^[\*\-•]\s+', '', stripped)
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.left_indent = Inches(0.25)
            # Clear default text and add formatted runs
            _add_formatted_runs(p, clean)
            for run in p.runs:
                run.font.size = Pt(10)
                run.font.name = 'Calibri'
            continue

        # Subtitle line (bold + italic): **text** on its own line right after name
        if stripped.startswith('**') and stripped.endswith('**') and stripped.count('**') == 2:
            inner = stripped.strip('*').strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(inner)
            run.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(80, 80, 80)
            continue

        # Contact/info line with pipes (centered)
        if '|' in stripped and len(stripped.split('|')) >= 3 and len(stripped) < 200:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(1)
            # Strip markdown link syntax: [text](url) → text
            clean_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', stripped)
            run = p.add_run(clean_text)
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(80, 80, 80)
            continue

        # Italic line: *text* (used for taglines/notes)
        if stripped.startswith('*') and stripped.endswith('*') and not stripped.startswith('**'):
            inner = stripped.strip('*').strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(inner)
            run.italic = True
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(100, 100, 100)
            continue

        # Project title line: **Project Name** | *tech stack* (date)
        if stripped.startswith('**') and ('|' in stripped or '—' in stripped):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(1)
            _add_formatted_runs(p, stripped)
            for run in p.runs:
                run.font.size = Pt(10)
                run.font.name = 'Calibri'
            continue

        # Regular paragraph with possible inline formatting
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        _add_formatted_runs(p, stripped)
        for run in p.runs:
            run.font.size = Pt(10)
            run.font.name = 'Calibri'

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def _build_cover_letter_docx(cover_letter: str, company: str = "") -> io.BytesIO:
    """Build a clean cover letter Word doc."""
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor

    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    style.font.color.rgb = RGBColor(33, 33, 33)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = Pt(15)

    paragraphs = cover_letter.strip().split('\n')
    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            doc.add_paragraph('')
        else:
            # Strip markdown formatting for cover letter
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)  # remove bold markers
            clean = re.sub(r'\*(.+?)\*', r'\1', clean)          # remove italic markers
            clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean)   # links → text only
            p = doc.add_paragraph(clean)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/{app_id}/download")
def download_application(
    app_id: str,
    doc_type: str = Query("resume", description="resume, cover_letter, or all"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download application materials as a Word document."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == user.id,
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id).first()
    company = job.company if job else "Company"
    safe_company = company.replace(' ', '_').replace('/', '_')[:30]

    if doc_type == "resume":
        if not app.tailored_resume:
            raise HTTPException(status_code=400, detail="No tailored resume available")
        buffer = _build_resume_docx(app.tailored_resume)
        filename = f"Resume_{safe_company}.docx"

    elif doc_type == "cover_letter":
        if not app.cover_letter:
            raise HTTPException(status_code=400, detail="No cover letter available")
        buffer = _build_cover_letter_docx(app.cover_letter, company)
        filename = f"Cover_Letter_{safe_company}.docx"

    else:
        raise HTTPException(status_code=400, detail="doc_type must be 'resume' or 'cover_letter'")

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )