"""Download routes — generate Word docs and ZIP bundles using templates."""

import io
import re
import zipfile
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from docx.shared import Pt, Inches, RGBColor

from database import get_db, User, Application, Job, Resume
from auth_core import get_current_user
from resume_templates import build_resume_from_template, TEMPLATES, parse_resume_markdown, _add_inline_formatting

router = APIRouter(prefix="/api/applications", tags=["downloads"])


# ── Template list endpoint ────────────────────────────────────────────

@router.get("/templates", tags=["templates"])
def list_templates():
    """List available resume templates."""
    return [
        {
            "id": k,
            "name": v["name"],
            "description": v["desc"],
            "requires_original": k == "user_template",
        }
        for k, v in TEMPLATES.items()
    ]


# ── Cover letter builder (no template needed) ────────────────────────

def _build_cover_letter_docx(cover_letter: str) -> io.BytesIO:
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


# ── Cheatsheet builder ────────────────────────────────────────────────

def _build_cheatsheet_docx(interview_prep: str, company_research: dict, job_title: str, company: str) -> io.BytesIO:
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

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Interview Cheat Sheet")
    run.bold = True
    run.font.size = Pt(16)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{job_title} — {company}")
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_paragraph('')

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
            for item in news[:3]:
                p = doc.add_paragraph(item, style='List Bullet')
                p.paragraph_format.space_after = Pt(1)

    doc.add_paragraph('')

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
            _add_inline_formatting(p, clean)
            p.paragraph_format.space_after = Pt(1)
            for run in p.runs:
                run.font.size = Pt(10)
        else:
            p = doc.add_paragraph()
            _add_inline_formatting(p, stripped)
            for run in p.runs:
                run.font.size = Pt(10)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# ── Download route ────────────────────────────────────────────────────

@router.get("/{app_id}/download")
def download_application(
    app_id: str,
    doc_type: str = Query("resume", description="resume, cover_letter, cheatsheet, or bundle"),
    template: str = Query("modern", description="classic, modern, or minimal"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download application materials. Resume uses the selected template."""
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

        # For "My Template", fetch the user's original DOCX bytes
        original_file = None
        if template == "user_template":
            active_resume = db.query(Resume).filter(
                Resume.user_id == user.id, Resume.is_active == True
            ).first()
            if active_resume and active_resume.original_file:
                original_file = active_resume.original_file
            else:
                raise HTTPException(
                    status_code=400,
                    detail="My Template requires a DOCX resume upload. Upload your resume as a .docx file first."
                )

        buffer = build_resume_from_template(app.tailored_resume, template, original_file=original_file)
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
        # For bundle with user_template, fetch original file once
        original_file = None
        if template == "user_template":
            active_resume = db.query(Resume).filter(
                Resume.user_id == user.id, Resume.is_active == True
            ).first()
            if active_resume and active_resume.original_file:
                original_file = active_resume.original_file

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            if app.tailored_resume:
                buf = build_resume_from_template(app.tailored_resume, template, original_file=original_file)
                zf.writestr(f"Resume_{safe_company}.docx", buf.read())
            if app.cover_letter:
                buf = _build_cover_letter_docx(app.cover_letter)
                zf.writestr(f"Cover_Letter_{safe_company}.docx", buf.read())
            if app.interview_prep:
                buf = _build_cheatsheet_docx(
                    app.interview_prep, app.company_research or {}, title, company
                )
                zf.writestr(f"Interview_Cheatsheet_{safe_company}.docx", buf.read())

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