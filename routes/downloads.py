"""Download routes — generate ATS-friendly Word docs and ZIP bundles.

The tailored resume comes from Gemini as Markdown text. This module
parses that Markdown and renders it into properly formatted Word
documents with real bold, italic, headings, bullets, and links.
"""

import io
import re
import zipfile
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
    pattern = r'(\*\*(.+?)\*\*|\*(.+?)\*|\[(.+?)\]\((.+?)\)|([^*\[\]]+))'

    for match in re.finditer(pattern, text):
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
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn

    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.65)
        section.right_margin = Inches(0.65)

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

        if not stripped:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            continue

        # H1: # Name
        if stripped.startswith('# ') and not stripped.startswith('##'):
            name = stripped.lstrip('# ').strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(name)
            run.bold = True
            run.font.size = Pt(18)
            run.font.color.rgb = RGBColor(0, 0, 0)
            continue

        # H2/H3: Section header
        if stripped.startswith('#'):
            heading_text = stripped.lstrip('#').strip().rstrip(':')
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10) if not is_first_heading else Pt(4)
            p.paragraph_format.space_after = Pt(3)
            is_first_heading = False

            run = p.add_run(heading_text.upper())
            run.bold = True
            run.font.size = Pt(10.5)
            run.font.color.rgb = RGBColor(0, 0, 0)

            pPr = p._element.get_or_add_pPr()
            pBdr = pPr.makeelement(qn('w:pBdr'), {})
            bottom = pBdr.makeelement(qn('w:bottom'), {
                qn('w:val'): 'single', qn('w:sz'): '4',
                qn('w:space'): '1', qn('w:color'): '444444',
            })
            pBdr.append(bottom)
            pPr.append(pBdr)
            continue

        if stripped in ('---', '***', '___'):
            continue

        # Bullet
        if re.match(r'^[\*\-•]\s', stripped):
            clean = re.sub(r'^[\*\-•]\s+', '', stripped)
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.left_indent = Inches(0.25)
            _add_formatted_runs(p, clean)
            for run in p.runs:
                run.font.size = Pt(10)
                run.font.name = 'Calibri'
            continue

        # Bold subtitle
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

        # Contact line with pipes
        if '|' in stripped and len(stripped.split('|')) >= 3 and len(stripped) < 200:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(1)
            clean_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', stripped)
            run = p.add_run(clean_text)
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(80, 80, 80)
            continue

        # Italic tagline
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

        # Project title line
        if stripped.startswith('**') and ('|' in stripped or '—' in stripped):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(1)
            _add_formatted_runs(p, stripped)
            for run in p.runs:
                run.font.size = Pt(10)
                run.font.name = 'Calibri'
            continue

        # Regular paragraph
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


def _build_cover_letter_docx(cover_letter: str) -> io.BytesIO:
    """Build a clean cover letter Word doc."""
    from docx import Document

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

    for para in cover_letter.strip().split('\n'):
        stripped = para.strip()
        if not stripped:
            doc.add_paragraph('')
        else:
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
            clean = re.sub(r'\*(.+?)\*', r'\1', clean)
            clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean)
            doc.add_paragraph(clean)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def _build_cheatsheet_docx(interview_prep: str, company_research: dict, job_title: str, company: str) -> io.BytesIO:
    """Build a concise interview cheat sheet — the night-before review doc."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn

    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(10)
    style.font.color.rgb = RGBColor(33, 33, 33)
    style.paragraph_format.space_after = Pt(2)

    # Title
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"Interview Cheat Sheet")
    run.bold = True
    run.font.size = Pt(16)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{job_title} — {company}")
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_paragraph('')

    # Company quick facts
    if company_research and isinstance(company_research, dict):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        run = p.add_run("COMPANY QUICK FACTS")
        run.bold = True
        run.font.size = Pt(10.5)

        facts = []
        if company_research.get("industry"):
            facts.append(f"Industry: {company_research['industry']}")
        if company_research.get("founded"):
            facts.append(f"Founded: {company_research['founded']}")
        if company_research.get("employee_count"):
            facts.append(f"Size: {company_research['employee_count']}")
        if company_research.get("description"):
            facts.append(company_research["description"])

        for fact in facts:
            p = doc.add_paragraph(fact, style='List Bullet')
            p.paragraph_format.space_after = Pt(1)

        news = company_research.get("recent_news", [])
        if news and news[0] != "Not found":
            p = doc.add_paragraph()
            run = p.add_run("Recent news to mention:")
            run.bold = True
            run.font.size = Pt(10)
            for item in news[:3]:
                p = doc.add_paragraph(item, style='List Bullet')
                p.paragraph_format.space_after = Pt(1)

    doc.add_paragraph('')

    # Interview prep content
    lines = interview_prep.strip().split('\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            doc.add_paragraph('')
            continue

        if stripped.startswith('#'):
            heading = stripped.lstrip('#').strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(3)
            run = p.add_run(heading.upper())
            run.bold = True
            run.font.size = Pt(10.5)

            pPr = p._element.get_or_add_pPr()
            pBdr = pPr.makeelement(qn('w:pBdr'), {})
            bottom = pBdr.makeelement(qn('w:bottom'), {
                qn('w:val'): 'single', qn('w:sz'): '4',
                qn('w:space'): '1', qn('w:color'): '444444',
            })
            pBdr.append(bottom)
            pPr.append(pBdr)
        elif re.match(r'^[\*\-•]\s', stripped):
            clean = re.sub(r'^[\*\-•]\s+', '', stripped)
            p = doc.add_paragraph(style='List Bullet')
            _add_formatted_runs(p, clean)
            p.paragraph_format.space_after = Pt(1)
            for run in p.runs:
                run.font.size = Pt(10)
        else:
            p = doc.add_paragraph()
            _add_formatted_runs(p, stripped)
            for run in p.runs:
                run.font.size = Pt(10)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/{app_id}/download")
def download_application(
    app_id: str,
    doc_type: str = Query("resume", description="resume, cover_letter, cheatsheet, or bundle"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download application materials as Word doc or ZIP bundle."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == user.id,
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id).first()
    company = job.company if job else "Company"
    title = job.title if job else "Position"
    safe_company = company.replace(' ', '_').replace('/', '_')[:30]

    if doc_type == "resume":
        if not app.tailored_resume:
            raise HTTPException(status_code=400, detail="No tailored resume available")
        buffer = _build_resume_docx(app.tailored_resume)
        filename = f"Resume_{safe_company}.docx"
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    elif doc_type == "cover_letter":
        if not app.cover_letter:
            raise HTTPException(status_code=400, detail="No cover letter available")
        buffer = _build_cover_letter_docx(app.cover_letter)
        filename = f"Cover_Letter_{safe_company}.docx"
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    elif doc_type == "cheatsheet":
        if not app.interview_prep:
            raise HTTPException(status_code=400, detail="No interview prep available")
        buffer = _build_cheatsheet_docx(
            app.interview_prep, app.company_research or {}, title, company
        )
        filename = f"Cheatsheet_{safe_company}.docx"
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    elif doc_type == "bundle":
        # ZIP bundle: resume + cover letter + cheatsheet
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            if app.tailored_resume:
                resume_buf = _build_resume_docx(app.tailored_resume)
                zf.writestr(f"Resume_{safe_company}.docx", resume_buf.read())

            if app.cover_letter:
                cl_buf = _build_cover_letter_docx(app.cover_letter)
                zf.writestr(f"Cover_Letter_{safe_company}.docx", cl_buf.read())

            if app.interview_prep:
                cs_buf = _build_cheatsheet_docx(
                    app.interview_prep, app.company_research or {}, title, company
                )
                zf.writestr(f"Interview_Cheatsheet_{safe_company}.docx", cs_buf.read())

        zip_buffer.seek(0)
        buffer = zip_buffer
        filename = f"Greenroom_{safe_company}_Application.zip"
        mime = "application/zip"

    else:
        raise HTTPException(status_code=400, detail="doc_type must be resume, cover_letter, cheatsheet, or bundle")

    return StreamingResponse(
        buffer,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )