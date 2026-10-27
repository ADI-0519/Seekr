from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.services.notes_generation import NotesResult

logger = logging.getLogger(__name__)

TEXT_PRIMARY = HexColor("#1A2B2E")
TEXT_SECONDARY = HexColor("#64748B")
TEXT_EMERALD = HexColor("#10B981")
BORDER = HexColor("#E2EDE8")


# Format raw seconds into a standard HH:MM:SS or MM:SS time string
def format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# Parse markdown text from the LLM and convert it into styled ReportLab elements
def markdown_to_paragraph(md_text: str, style: ParagraphStyle) -> list:
    elements = []

    for line in md_text.split("\n"):
        # Preserve indent before stripping to calculate nesting level
        stripped = line.lstrip(" ")
        level = (len(line) - len(stripped)) // 2
        stripped = stripped.strip()

        if not stripped:
            elements.append(Spacer(1, 4))
            continue

        # Normalise any bullet glyph the LLM might emit to plain dash
        for glyph in ("\u25a0", "\u25cf", "\u2022", "\u25e6", "\u2013", "\u2014"):
            if stripped.startswith(glyph + " "):
                stripped = "- " + stripped[len(glyph) + 1 :]
                break
            elif stripped.startswith(glyph):
                stripped = "- " + stripped[len(glyph) :].lstrip()
                break

        stripped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
        stripped = re.sub(r"\*(.+?)\*", r"<i>\1</i>", stripped)
        stripped = re.sub(r"`(.+?)`", r'<font face="Courier" size="9">\1</font>', stripped)
        # braced notation e.g. A_{i-1} or x^{2}
        stripped = re.sub(r"_\{([^}]+)\}", r"<sub>\1</sub>", stripped)
        stripped = re.sub(r"\^\{([^}]+)\}", r"<sup>\1</sup>", stripped)
        # bare single-char notation e.g. f_t or x^2
        stripped = re.sub(r"_([A-Za-z0-9])", r"<sub>\1</sub>", stripped)
        stripped = re.sub(r"\^([A-Za-z0-9])", r"<sup>\1</sup>", stripped)

        if stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:]
            bullet = "-"
            bullet_style = ParagraphStyle(
                f"bullet_l{level}",
                parent=style,
                leftIndent=8 + level * 18,
                firstLineIndent=-8,
            )
            elements.append(Paragraph(f"{bullet}  {text}", bullet_style))
        elif level > 0:
            body_style = ParagraphStyle(
                f"body_l{level}",
                parent=style,
                leftIndent=level * 18,
            )
            elements.append(Paragraph(stripped, body_style))
        else:
            elements.append(Paragraph(stripped, style))

    return elements


# Compile a complete PDF document in memory containing the lecture table of contents and study notes
def generate_notes_pdf(
    lecture_title: str,
    notes: list[NotesResult],
    lecture_duration: float | None = None,
) -> io.BytesIO:
    buffer = io.BytesIO()

    # Initialize the PDF template with standard A4 sizing and margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Lecture Notes - {lecture_title}",
        author="Seekr",
    )

    styles = getSampleStyleSheet()

    # Define custom typography styles
    title_style = ParagraphStyle(
        "LectureTitle",
        parent=styles["Title"],
        fontSize=28,
        leading=34,
        textColor=TEXT_PRIMARY,
        spaceAfter=8,
        fontName="Helvetica-Bold",
    )

    section_title_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading1"],
        fontSize=16,
        leading=22,
        textColor=TEXT_EMERALD,
        spaceBefore=16,
        spaceAfter=8,
        fontName="Helvetica-Bold",
    )

    timestamp_style = ParagraphStyle(
        "Timestamp",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=TEXT_SECONDARY,
        spaceAfter=12,
        fontName="Helvetica",
    )

    body_style = ParagraphStyle(
        "NotesBody",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
        textColor=TEXT_PRIMARY,
        spaceAfter=4,
        fontName="Helvetica",
    )

    toc_style = ParagraphStyle(
        "TOCEntry",
        parent=styles["Normal"],
        fontSize=11,
        leading=18,
        textColor=TEXT_PRIMARY,
        fontName="Helvetica",
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=TEXT_SECONDARY,
        fontName="Helvetica",
    )

    story = []

    # Build the title page header
    story.append(Spacer(1, 40))
    story.append(Paragraph(lecture_title, title_style))

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=BORDER,
            spaceBefore=12,
            spaceAfter=24,
        )
    )

    # Build the table of contents listing each segment title and timestamp
    story.append(Paragraph("Contents", section_title_style))
    story.append(Spacer(1, 8))

    for i, note in enumerate(notes, 1):
        ts = format_timestamp(note.start_time)
        toc_text = f"{i}. {note.title}  <font color='#64748B'>({ts})</font>"
        story.append(Paragraph(toc_text, toc_style))

    story.append(PageBreak())

    # Build the core document body by rendering each generated note
    for i, note in enumerate(notes, 1):
        ts_start = format_timestamp(note.start_time)
        ts_end = format_timestamp(note.end_time)

        story.append(Paragraph(f"{i}. {note.title}", section_title_style))
        story.append(Paragraph(f"{ts_start} - {ts_end}", timestamp_style))

        note_elements = markdown_to_paragraph(note.notes_markdown, body_style)
        story.extend(note_elements)

        story.append(Spacer(1, 12))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=BORDER,
                spaceBefore=8,
                spaceAfter=16,
            )
        )

    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    story.append(Spacer(1, 20))
    story.append(
        Paragraph(
            f"Generated by Seekr - {now}",
            footer_style,
        )
    )

    # Render the document to the byte buffer and return it
    doc.build(story)
    buffer.seek(0)
    return buffer
