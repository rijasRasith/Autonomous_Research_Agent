import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

BRAND_PURPLE = colors.HexColor("#6366f1")
BRAND_DARK = colors.HexColor("#1e1b4b")
TEXT_DARK = colors.HexColor("#1f2937")
TEXT_MUTED = colors.HexColor("#6b7280")


def _to_str(item: Any) -> str:
    """
    Safely coerce any LLM-returned item to a plain string for ReportLab.
    Handles strings, dicts (e.g. {"point": "...", "detail": "..."}), and lists.
    Also escapes ReportLab XML special characters.
    """
    if isinstance(item, str):
        text = item
    elif isinstance(item, dict):
        # Try common key names first; fall back to joining all values
        for key in ("point", "text", "content", "finding", "insight", "title", "description"):
            if key in item:
                text = str(item[key])
                break
        else:
            text = " — ".join(str(v) for v in item.values() if v)
    elif isinstance(item, (list, tuple)):
        text = " | ".join(_to_str(x) for x in item)
    else:
        text = str(item)

    # Escape XML special chars that ReportLab can't handle in Paragraph
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.strip()


def _build_styles() -> dict:
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontSize=22,
            textColor=BRAND_DARK,
            spaceAfter=6,
            fontName="Helvetica-Bold",
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontSize=9,
            textColor=TEXT_MUTED,
            spaceAfter=4,
        ),
        "section_header": ParagraphStyle(
            "SectionHeader",
            parent=base["Heading2"],
            fontSize=13,
            textColor=BRAND_PURPLE,
            spaceBefore=14,
            spaceAfter=6,
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "BodyText",
            parent=base["Normal"],
            fontSize=10,
            textColor=TEXT_DARK,
            spaceAfter=8,
            leading=15,
        ),
        "bullet": ParagraphStyle(
            "BulletText",
            parent=base["Normal"],
            fontSize=10,
            textColor=TEXT_DARK,
            spaceAfter=4,
            leading=14,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontSize=8,
            textColor=TEXT_MUTED,
            alignment=1,
        ),
    }
    return styles


class PDFExporter:

    def export(self, query: str, summary: dict, raw_results: list, metadata: dict) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^\w\s-]", "", query[:40]).strip().replace(" ", "_")
        filename = f"report_{safe_name}_{timestamp}.pdf"

        reports_dir = Path(settings.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        filepath = reports_dir / filename

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=inch * 0.9,
            leftMargin=inch * 0.9,
            topMargin=inch * 0.9,
            bottomMargin=inch * 0.9,
        )

        story = self._build_story(query, summary, raw_results, metadata, timestamp)
        doc.build(story)

        logger.info(f"[PDFExporter] Saved: {filepath}")
        return str(filepath)

    def _build_story(
        self,
        query: str,
        summary: dict,
        raw_results: list,
        metadata: dict,
        timestamp: str,
    ) -> list:
        styles = _build_styles()
        story = []

        # ── Header ──────────────────────────────────────────────────────────
        story.append(Paragraph("Research Report", styles["title"]))
        story.append(Paragraph(f"<b>Query:</b> {_to_str(query)}", styles["body"]))
        story.append(Paragraph(f"Generated: {timestamp} UTC", styles["meta"]))
        tools_str = ", ".join(str(t) for t in metadata.get("tools_used", []))
        story.append(Paragraph(
            f"Tools: {tools_str} | "
            f"Iterations: {metadata.get('iterations', 1)} | "
            f"Sources: {metadata.get('sources_count', len(raw_results))}",
            styles["meta"],
        ))
        story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_PURPLE, spaceAfter=10))

        # ── Executive Summary ───────────────────────────────────────────────
        exec_summary = summary.get("executive_summary", "")
        if exec_summary:
            story.append(Paragraph("Executive Summary", styles["section_header"]))
            story.append(Paragraph(_to_str(exec_summary), styles["body"]))
            story.append(Spacer(1, 6))

        # ── Key Points ──────────────────────────────────────────────────────
        key_points = summary.get("key_points", [])
        if key_points:
            story.append(Paragraph("Key Points", styles["section_header"]))
            try:
                items = [
                    ListItem(Paragraph(_to_str(p), styles["bullet"]), bulletColor=BRAND_PURPLE)
                    for p in key_points
                ]
                story.append(ListFlowable(items, bulletType="bullet"))
            except Exception as e:
                logger.warning(f"[PDFExporter] key_points render fallback: {e}")
                for p in key_points:
                    story.append(Paragraph(f"• {_to_str(p)}", styles["bullet"]))
            story.append(Spacer(1, 6))

        # ── Important Findings ──────────────────────────────────────────────
        findings = summary.get("important_findings", [])
        if findings:
            story.append(Paragraph("Important Findings", styles["section_header"]))
            try:
                items = [
                    ListItem(Paragraph(_to_str(f), styles["bullet"]), bulletColor=BRAND_PURPLE)
                    for f in findings
                ]
                story.append(ListFlowable(items, bulletType="bullet"))
            except Exception as e:
                logger.warning(f"[PDFExporter] findings render fallback: {e}")
                for f in findings:
                    story.append(Paragraph(f"• {_to_str(f)}", styles["bullet"]))
            story.append(Spacer(1, 6))

        # ── Actionable Insights ─────────────────────────────────────────────
        insights = summary.get("actionable_insights", [])
        if insights:
            story.append(Paragraph("Actionable Insights", styles["section_header"]))
            try:
                items = [
                    ListItem(Paragraph(_to_str(i), styles["bullet"]), bulletColor=BRAND_PURPLE)
                    for i in insights
                ]
                story.append(ListFlowable(items, bulletType="bullet"))
            except Exception as e:
                logger.warning(f"[PDFExporter] insights render fallback: {e}")
                for i in insights:
                    story.append(Paragraph(f"• {_to_str(i)}", styles["bullet"]))
            story.append(Spacer(1, 6))

        # ── References ──────────────────────────────────────────────────────
        references = summary.get("references", [])
        if references:
            story.append(Paragraph("References", styles["section_header"]))
            for ref in references:
                try:
                    if isinstance(ref, dict):
                        title = _to_str(ref.get("title", "Unknown"))
                        url = _to_str(ref.get("url", ""))
                        relevance = _to_str(ref.get("relevance", ""))
                        text = f"<b>{title}</b>"
                        if url:
                            text += f" — {url}"
                        if relevance:
                            text += f" <i>({relevance})</i>"
                        story.append(Paragraph(text, styles["bullet"]))
                    else:
                        story.append(Paragraph(_to_str(ref), styles["bullet"]))
                except Exception as e:
                    logger.warning(f"[PDFExporter] reference render error: {e}")

        # ── Footer ──────────────────────────────────────────────────────────
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=0.5, color=TEXT_MUTED))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Generated by Autonomous Research Agent", styles["footer"]))

        return story
