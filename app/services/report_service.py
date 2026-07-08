import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import Insight, ProductIntelligenceReport

_STYLES = getSampleStyleSheet()
_QUOTE_STYLE = ParagraphStyle(
    "Quote", parent=_STYLES["Italic"], leftIndent=18, spaceAfter=6, textColor=colors.grey
)


def _insight_flowables(insights: list[Insight], report: ProductIntelligenceReport) -> list:
    flowables = []
    if not insights:
        flowables.append(Paragraph("None identified.", _STYLES["BodyText"]))
        return flowables

    for insight in insights:
        heading = f"{insight.title} — mentioned {insight.frequency} time(s)"
        if insight.severity:
            heading += f" (severity: {insight.severity})"
        flowables.append(Paragraph(heading, _STYLES["Heading3"]))
        for rid in insight.supporting_review_ids[:3]:
            review = report.reviews_by_id.get(rid)
            if review:
                flowables.append(
                    Paragraph(f'"{review.text}" — {review.author}', _QUOTE_STYLE)
                )
        flowables.append(Spacer(1, 8))
    return flowables


def generate_pdf(report: ProductIntelligenceReport) -> bytes:
    """Render a ProductIntelligenceReport as a PDF and return its bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []

    story.append(Paragraph("InsightQT — Product Intelligence Report", _STYLES["Title"]))
    story.append(Paragraph(report.app_name, _STYLES["Heading2"]))
    story.append(
        Paragraph(
            f"Platform: {report.platform.replace('_', ' ').title()} · "
            f"Rating: {report.overall_rating:.1f}/5 · "
            f"Reviews analyzed: {report.reviews_analyzed}",
            _STYLES["BodyText"],
        )
    )
    story.append(Spacer(1, 16))

    story.append(Paragraph("Executive Summary", _STYLES["Heading1"]))
    story.append(Paragraph(report.executive_summary, _STYLES["BodyText"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Overall Sentiment", _STYLES["Heading1"]))
    sentiment = report.overall_sentiment
    table = Table(
        [
            ["Positive", "Neutral", "Negative"],
            [
                f"{sentiment.get('positive_pct', 0):.0f}%",
                f"{sentiment.get('neutral_pct', 0):.0f}%",
                f"{sentiment.get('negative_pct', 0):.0f}%",
            ],
        ],
        colWidths=[1.8 * inch] * 3,
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(table)
    story.append(PageBreak())

    story.append(Paragraph("Top Customer Problems", _STYLES["Heading1"]))
    story.extend(_insight_flowables(report.top_problems, report))

    story.append(Paragraph("Feature Requests", _STYLES["Heading1"]))
    story.extend(_insight_flowables(report.feature_requests, report))

    story.append(Paragraph("Positive Feedback", _STYLES["Heading1"]))
    story.extend(_insight_flowables(report.positive_feedback, report))

    story.append(Paragraph("Critical Issues", _STYLES["Heading1"]))
    story.extend(_insight_flowables(report.critical_issues, report))

    doc.build(story)
    return buffer.getvalue()
