"""
User Template — clone the user's original DOCX and replace content.

Approach:
  1. Open the original DOCX to extract a "format profile" — the exact
     paragraph properties (pPr) and run properties (rPr) for each
     paragraph role (name, subtitle, section header, skill line, etc.)
  2. Clone the document bytes (preserves margins, styles, theme, fonts)
  3. Strip all paragraphs from the clone
  4. Rebuild content using the parsed tailored Markdown + extracted profiles

This preserves the user's exact visual identity — borders, spacing, tab
stops, font choices — while swapping in AI-tailored content.
"""

import io
import copy
import re
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

from resume_templates import parse_resume_markdown


# ── Namespace shorthand ──────────────────────────────────────────────

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


# ── Format profile extraction ───────────────────────────────────────

def _has_border(p) -> bool:
    """Check if a paragraph has a bottom border (pBdr)."""
    pPr = p._element.find(qn("w:pPr"))
    if pPr is None:
        return False
    pBdr = pPr.find(qn("w:pBdr"))
    return pBdr is not None


def _is_bold(p) -> bool:
    """Check if the first run of a paragraph is bold."""
    if not p.runs:
        return False
    return p.runs[0].bold is True


def _is_uppercase_text(text: str) -> bool:
    """Check if text is all uppercase (ignoring non-alpha chars)."""
    alpha = "".join(c for c in text if c.isalpha())
    return len(alpha) >= 2 and alpha == alpha.upper()


def _is_section_header(p) -> bool:
    """Detect section headers: bold + uppercase + bottom border."""
    text = p.text.strip()
    if not text:
        return False
    return _is_bold(p) and _is_uppercase_text(text) and _has_border(p)


def _has_tab_stop(p) -> bool:
    """Check if paragraph has a tab stop defined."""
    pPr = p._element.find(qn("w:pPr"))
    if pPr is None:
        return False
    return pPr.find(qn("w:tabs")) is not None


def _get_space_before(p) -> int:
    """Get space_before in EMU, 0 if not set."""
    sb = p.paragraph_format.space_before
    return sb if sb and isinstance(sb, int) else 0


def _get_space_after(p) -> int:
    """Get space_after in EMU, 0 if not set."""
    sa = p.paragraph_format.space_after
    return sa if sa and isinstance(sa, int) else 0


def _clone_pPr(source_p):
    """Deep-copy a paragraph's <w:pPr> element, or None if absent."""
    pPr = source_p._element.find(qn("w:pPr"))
    if pPr is not None:
        return copy.deepcopy(pPr)
    return None


def _clone_rPr(source_run):
    """Deep-copy a run's <w:rPr> element, or None if absent."""
    rPr = source_run._element.find(qn("w:rPr"))
    if rPr is not None:
        return copy.deepcopy(rPr)
    return None


class FormatProfile:
    """Extracted formatting templates from the user's original DOCX.

    Each field holds a (pPr_xml, rPr_xml) tuple — the paragraph properties
    and the first run's properties as deep-copied lxml elements.
    """

    def __init__(self):
        # Header zone
        self.name = None           # (pPr, rPr) — the big bold name
        self.subtitle = None       # (pPr, rPr) — e.g. "AI & Web Developer"
        self.contact = None        # (pPr, rPr) — contact lines
        self.tagline = None        # (pPr, rPr) — "· Remote-friendly ·"

        # Section elements
        self.section_heading = None  # (pPr, rPr) — bold uppercase with border
        self.plain_text = None       # (pPr, rPr) — normal content paragraph
        self.skill_line_bold = None  # rPr for the bold category part
        self.skill_line_normal = None  # rPr for the comma-separated items
        self.skill_pPr = None        # pPr for skill lines
        self.entry_title_pPr = None  # pPr for project/edu title (has tabs)
        self.entry_title_rPr_bold = None  # rPr for bold title part
        self.entry_title_rPr_date = None  # rPr for date/year part
        self.sub_line = None         # (pPr, rPr) — tech stack / institution
        self.content_para = None     # (pPr, rPr) — bullet / description
        self.repo_line = None        # (pPr, rPr) — repo links (larger space_after)

        # Page margins (EMU values)
        self.margin_top = None
        self.margin_bottom = None
        self.margin_left = None
        self.margin_right = None


def extract_format_profile(doc: Document) -> FormatProfile:
    """Walk the document and extract formatting for each paragraph role."""
    profile = FormatProfile()
    paras = doc.paragraphs

    # Margins
    sec = doc.sections[0]
    profile.margin_top = sec.top_margin
    profile.margin_bottom = sec.bottom_margin
    profile.margin_left = sec.left_margin
    profile.margin_right = sec.right_margin

    # Find first section header index
    first_header_idx = None
    for i, p in enumerate(paras):
        if _is_section_header(p):
            first_header_idx = i
            break

    if first_header_idx is None:
        first_header_idx = len(paras)

    # ── Extract header zone formatting (before first section) ────────

    header_zone = paras[:first_header_idx]
    header_roles_assigned = {"name": False, "subtitle": False, "contact": False, "tagline": False}

    for p in header_zone:
        text = p.text.strip()
        if not text:
            continue

        pPr = _clone_pPr(p)
        rPr = _clone_rPr(p.runs[0]) if p.runs else None

        # Name: usually first bold paragraph, or largest font
        if _is_bold(p) and not header_roles_assigned["name"]:
            font_size = p.runs[0].font.size if p.runs else None
            if font_size and font_size > 150000:  # > ~12pt in EMU
                profile.name = (pPr, rPr)
                header_roles_assigned["name"] = True
                continue

        # Subtitle: bold, not the name
        if _is_bold(p) and header_roles_assigned["name"] and not header_roles_assigned["subtitle"]:
            profile.subtitle = (pPr, rPr)
            header_roles_assigned["subtitle"] = True
            continue

        # Contact: has pipes
        if "|" in text and not header_roles_assigned["contact"]:
            profile.contact = (pPr, rPr)
            header_roles_assigned["contact"] = True
            continue

        # Tagline: has middle dots or is remaining
        if "·" in text and not header_roles_assigned["tagline"]:
            profile.tagline = (pPr, rPr)
            header_roles_assigned["tagline"] = True
            continue

    # If name wasn't detected by font size, use first non-empty paragraph
    if not header_roles_assigned["name"] and header_zone:
        for p in header_zone:
            if p.text.strip():
                profile.name = (_clone_pPr(p), _clone_rPr(p.runs[0]) if p.runs else None)
                break

    # ── Extract section content formatting ───────────────────────────

    in_section = False
    prev_was_entry_title = False

    for i, p in enumerate(paras):
        text = p.text.strip()

        # Section header formatting
        if _is_section_header(p) and profile.section_heading is None:
            profile.section_heading = (_clone_pPr(p), _clone_rPr(p.runs[0]) if p.runs else None)
            in_section = True
            prev_was_entry_title = False
            continue

        if not in_section:
            continue

        if not text:
            prev_was_entry_title = False
            continue

        pPr = _clone_pPr(p)

        # Skill line: bold first run + contains ":"
        if _is_bold(p) and ":" in text and len(p.runs) >= 2 and profile.skill_line_bold is None:
            profile.skill_pPr = pPr
            profile.skill_line_bold = _clone_rPr(p.runs[0])
            profile.skill_line_normal = _clone_rPr(p.runs[1])
            prev_was_entry_title = False
            continue

        # Entry title: bold + has tab stop (project/edu title with date)
        if _is_bold(p) and _has_tab_stop(p) and profile.entry_title_pPr is None:
            profile.entry_title_pPr = pPr
            profile.entry_title_rPr_bold = _clone_rPr(p.runs[0])
            # Date part: find the run after the tab
            for r in p.runs:
                if "\t" in r.text:
                    continue
                if not r.bold:
                    profile.entry_title_rPr_date = _clone_rPr(r)
                    break
            if profile.entry_title_rPr_date is None and len(p.runs) > 1:
                profile.entry_title_rPr_date = _clone_rPr(p.runs[-1])
            prev_was_entry_title = True
            continue

        # Sub-line: right after entry title, low space_after (~17780)
        if prev_was_entry_title and profile.sub_line is None:
            rPr = _clone_rPr(p.runs[0]) if p.runs else None
            profile.sub_line = (pPr, rPr)
            prev_was_entry_title = False
            continue

        # Repo line: starts with "Repo:" or contains "github.com/"
        if ("repo:" in text.lower() or "github.com/" in text.lower()) and profile.repo_line is None:
            rPr = _clone_rPr(p.runs[0]) if p.runs else None
            profile.repo_line = (pPr, rPr)
            prev_was_entry_title = False
            continue

        # Content paragraph (bullets, descriptions)
        if profile.content_para is None:
            rPr = _clone_rPr(p.runs[0]) if p.runs else None
            profile.content_para = (pPr, rPr)

        prev_was_entry_title = False

    # Fallback: if plain_text wasn't set, use content_para
    if profile.plain_text is None:
        profile.plain_text = profile.content_para

    return profile


# ── Document building helpers ────────────────────────────────────────

def _make_paragraph(body, pPr=None) -> "Paragraph":
    """Create a new <w:p> element and append it to the body, returning a Paragraph wrapper."""
    from docx.text.paragraph import Paragraph

    p_elem = body.makeelement(qn("w:p"), {})
    if pPr is not None:
        p_elem.append(copy.deepcopy(pPr))
    body.append(p_elem)

    # Wrap in python-docx Paragraph object for convenience
    return Paragraph(p_elem, body)


def _add_run(paragraph, text: str, rPr=None):
    """Add a run with text to a paragraph, applying rPr formatting."""
    r_elem = paragraph._element.makeelement(qn("w:r"), {})
    if rPr is not None:
        r_elem.append(copy.deepcopy(rPr))
    t_elem = r_elem.makeelement(qn("w:t"), {})
    t_elem.text = text
    # Preserve whitespace
    t_elem.set(qn("xml:space"), "preserve")
    r_elem.append(t_elem)
    paragraph._element.append(r_elem)


def _add_tab_run(paragraph, rPr=None):
    """Add a run containing a tab character."""
    r_elem = paragraph._element.makeelement(qn("w:r"), {})
    if rPr is not None:
        r_elem.append(copy.deepcopy(rPr))
    tab_elem = r_elem.makeelement(qn("w:tab"), {})
    r_elem.append(tab_elem)
    paragraph._element.append(r_elem)


def _strip_markdown_bold(text: str) -> list:
    """Parse **bold** and regular text into segments.

    Returns list of (text, is_bold) tuples.
    """
    segments = []
    pattern = r"\*\*(.+?)\*\*"
    last_end = 0
    for m in re.finditer(pattern, text):
        if m.start() > last_end:
            segments.append((text[last_end:m.start()], False))
        segments.append((m.group(1), True))
        last_end = m.end()
    if last_end < len(text):
        segments.append((text[last_end:], False))
    return segments if segments else [(text, False)]


# ── Main builder ─────────────────────────────────────────────────────

def build_user_template(markdown: str, original_bytes: bytes) -> io.BytesIO:
    """Build a resume using the user's original DOCX as the formatting source.

    1. Extract format profiles from the original document
    2. Clone the document (preserving margins, styles, theme, fonts)
    3. Remove all existing paragraphs
    4. Write new content using the extracted profiles

    Args:
        markdown: Gemini's tailored resume in Markdown format
        original_bytes: The raw bytes of the user's original DOCX file

    Returns:
        BytesIO buffer containing the new DOCX
    """
    # Parse the tailored markdown into structured sections
    sections = parse_resume_markdown(markdown)

    # Extract formatting from the original
    original_doc = Document(io.BytesIO(original_bytes))
    profile = extract_format_profile(original_doc)

    # Clone the document (binary copy preserves everything)
    clone = Document(io.BytesIO(original_bytes))
    body = clone.element.body

    # Remove all existing paragraphs
    for p_elem in list(body.findall(qn("w:p"))):
        body.remove(p_elem)

    # ── Write header zone ────────────────────────────────────────────

    # Name
    if sections["name"]:
        pPr, rPr = profile.name or (None, None)
        p = _make_paragraph(body, pPr)
        _add_run(p, sections["name"], rPr)

    # Subtitle
    if sections["subtitle"]:
        pPr, rPr = profile.subtitle or (None, None)
        p = _make_paragraph(body, pPr)
        _add_run(p, sections["subtitle"], rPr)

    # Contact — split on newlines if present, otherwise single line
    if sections["contact"]:
        contact_lines = sections["contact"].split("\n")
        for line in contact_lines:
            line = line.strip()
            if not line:
                continue
            pPr, rPr = profile.contact or (None, None)
            p = _make_paragraph(body, pPr)
            _add_run(p, line, rPr)

    # Tagline
    if sections["tagline"]:
        pPr, rPr = profile.tagline or (None, None)
        p = _make_paragraph(body, pPr)
        _add_run(p, sections["tagline"], rPr)

    # ── Write each section ───────────────────────────────────────────

    for sec in sections["sections"]:
        heading = sec["heading"]
        content = sec["content"]

        # Section header
        pPr, rPr = profile.section_heading or (None, None)
        p = _make_paragraph(body, pPr)
        _add_run(p, heading.upper(), rPr)

        # Detect content type from the heading name
        heading_upper = heading.upper().strip()

        if _is_skills_section(heading_upper):
            _write_skills_content(body, content, profile)
        elif _is_projects_or_experience_section(heading_upper):
            _write_entries_content(body, content, profile)
        elif _is_education_section(heading_upper):
            _write_education_content(body, content, profile)
        else:
            _write_generic_content(body, content, profile)

    buf = io.BytesIO()
    clone.save(buf)
    buf.seek(0)
    return buf


# ── Section type detection ───────────────────────────────────────────

_SKILLS_KEYWORDS = {"TECHNICAL SKILLS", "SKILLS", "CORE COMPETENCIES", "TECHNOLOGIES"}
_ENTRY_KEYWORDS = {"PROJECTS", "EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "EMPLOYMENT"}
_EDUCATION_KEYWORDS = {"EDUCATION", "ACADEMIC BACKGROUND", "QUALIFICATIONS"}


def _is_skills_section(heading: str) -> bool:
    return heading in _SKILLS_KEYWORDS or "SKILL" in heading


def _is_projects_or_experience_section(heading: str) -> bool:
    return heading in _ENTRY_KEYWORDS or "PROJECT" in heading or "EXPERIENCE" in heading


def _is_education_section(heading: str) -> bool:
    return heading in _EDUCATION_KEYWORDS or "EDUCATION" in heading


# ── Content writers ──────────────────────────────────────────────────

def _write_skills_content(body, content: list, profile: FormatProfile):
    """Write skill lines: 'Category:  value, value, value'"""
    for item in content:
        text = item if isinstance(item, str) else item.get("bullet", str(item))
        text = _strip_markdown_stars(text)

        pPr = profile.skill_pPr
        p = _make_paragraph(body, pPr)

        # Try to split "Category:  items" or "Category: items"
        colon_match = re.match(r"^([^:]+):\s*(.*)", text)
        if colon_match and profile.skill_line_bold is not None:
            category = colon_match.group(1).strip()
            items = colon_match.group(2).strip()
            _add_run(p, category + ":  ", profile.skill_line_bold)
            _add_run(p, items, profile.skill_line_normal)
        else:
            # No colon pattern — write as plain text with normal rPr
            rPr = profile.skill_line_normal or (profile.content_para or (None, None))[1]
            _add_run(p, text, rPr)


def _write_entries_content(body, content: list, profile: FormatProfile):
    """Write project/experience entries.

    Expected Markdown patterns from Gemini:
      - "**Title — Description**\\tYear" (entry title with tab-aligned date)
      - "Title — Description" (entry title without date)
      - "Python, FastAPI, React" (tech stack line, after title)
      - "- bullet point" (regular bullet)
      - "Repo: github.com/..." (repo link)
      - Any other text (description paragraph)
    """
    prev_was_title = False

    for item in content:
        if isinstance(item, dict) and "bullet" in item:
            # Bullet point
            text = _strip_markdown_stars(item["bullet"])
            pPr, rPr = profile.content_para or (None, None)
            p = _make_paragraph(body, pPr)
            _add_run(p, "• " + text, rPr)
            prev_was_title = False
            continue

        text = item if isinstance(item, str) else str(item)
        text = text.strip()
        if not text:
            continue

        clean = _strip_markdown_stars(text)

        # Detect entry title: bold markdown + possible tab/date pattern
        is_title_line = text.startswith("**") and ("**" in text[2:])

        # Check for tab-separated date pattern: "Title\tDate"
        tab_match = re.match(r"^(.+?)\t(.+)$", clean)
        # Or "Title | Date" pattern Gemini sometimes uses
        pipe_date = re.match(r"^(.+?)\s*\|\s*(\d{2}/\d{4}\s*[-–]\s*.+|\d{4}\s*[-–]\s*.+|\d{4})$", clean)

        if is_title_line or tab_match:
            # Entry title line
            pPr = profile.entry_title_pPr
            p = _make_paragraph(body, pPr)

            if tab_match:
                title_part = _strip_markdown_stars(tab_match.group(1))
                date_part = tab_match.group(2).strip()
            elif pipe_date:
                title_part = _strip_markdown_stars(pipe_date.group(1))
                date_part = pipe_date.group(2).strip()
            else:
                # Just bold title, no date
                title_part = clean
                date_part = None

            _add_run(p, title_part, profile.entry_title_rPr_bold)
            if date_part:
                _add_tab_run(p, profile.entry_title_rPr_date)
                _add_run(p, date_part, profile.entry_title_rPr_date)
            prev_was_title = True
            continue

        # Tech stack / sub-line (right after a title)
        if prev_was_title and _looks_like_tech_stack(clean):
            pPr, rPr = profile.sub_line or profile.content_para or (None, None)
            p = _make_paragraph(body, pPr)
            _add_run(p, clean, rPr)
            prev_was_title = False
            continue

        # Repo line
        if clean.lower().startswith("repo:") or "github.com/" in clean.lower():
            pPr, rPr = profile.repo_line or profile.sub_line or profile.content_para or (None, None)
            p = _make_paragraph(body, pPr)
            _add_run(p, clean, rPr)
            prev_was_title = False
            continue

        # Regular content paragraph
        pPr, rPr = profile.content_para or (None, None)
        p = _make_paragraph(body, pPr)
        _add_run(p, clean, rPr)
        prev_was_title = False


def _write_education_content(body, content: list, profile: FormatProfile):
    """Write education entries — similar to projects but with institution lines."""
    prev_was_title = False

    for item in content:
        if isinstance(item, dict) and "bullet" in item:
            text = _strip_markdown_stars(item["bullet"])
            pPr, rPr = profile.content_para or (None, None)
            p = _make_paragraph(body, pPr)
            _add_run(p, text, rPr)
            prev_was_title = False
            continue

        text = item if isinstance(item, str) else str(item)
        text = text.strip()
        if not text:
            continue

        clean = _strip_markdown_stars(text)

        # Education title: bold + date (e.g. "M.Sc. Digital Technologies\t04/2024 – Present")
        is_title = text.startswith("**") and ("**" in text[2:])
        tab_match = re.match(r"^(.+?)\t(.+)$", clean)
        pipe_date = re.match(r"^(.+?)\s*\|\s*(\d{2}/\d{4}\s*[-–]\s*.+|\d{4}\s*[-–]\s*.+|\d{4})$", clean)

        if is_title or tab_match:
            pPr = profile.entry_title_pPr
            p = _make_paragraph(body, pPr)

            if tab_match:
                title_part = _strip_markdown_stars(tab_match.group(1))
                date_part = tab_match.group(2).strip()
            elif pipe_date:
                title_part = _strip_markdown_stars(pipe_date.group(1))
                date_part = pipe_date.group(2).strip()
            else:
                title_part = clean
                date_part = None

            _add_run(p, title_part, profile.entry_title_rPr_bold)
            if date_part:
                _add_tab_run(p, profile.entry_title_rPr_date)
                _add_run(p, date_part, profile.entry_title_rPr_date)
            prev_was_title = True
            continue

        # Institution / sub-line
        if prev_was_title:
            pPr, rPr = profile.sub_line or profile.content_para or (None, None)
            p = _make_paragraph(body, pPr)
            _add_run(p, clean, rPr)
            prev_was_title = False
            continue

        # Regular content (coursework, etc.)
        pPr, rPr = profile.content_para or (None, None)
        p = _make_paragraph(body, pPr)
        _add_run(p, clean, rPr)
        prev_was_title = False


def _write_generic_content(body, content: list, profile: FormatProfile):
    """Write a section that doesn't match known patterns — PROFILE, LANGUAGES, etc."""
    for item in content:
        if isinstance(item, dict) and "bullet" in item:
            text = _strip_markdown_stars(item["bullet"])
            pPr, rPr = profile.content_para or (None, None)
            p = _make_paragraph(body, pPr)
            _add_run(p, "• " + text, rPr)
        else:
            text = item if isinstance(item, str) else str(item)
            clean = _strip_markdown_stars(text.strip())
            if not clean:
                continue
            pPr, rPr = profile.content_para or (None, None)
            p = _make_paragraph(body, pPr)
            _add_run(p, clean, rPr)


# ── Text helpers ─────────────────────────────────────────────────────

def _strip_markdown_stars(text: str) -> str:
    """Remove **bold** and *italic* markers from text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)  # [link](url) → link
    return text


def _looks_like_tech_stack(text: str) -> bool:
    """Heuristic: a short comma-separated list of technologies."""
    if len(text) > 200:
        return False
    commas = text.count(",")
    words = len(text.split())
    # Tech stacks tend to have many commas relative to word count
    return commas >= 2 and commas > words * 0.15
