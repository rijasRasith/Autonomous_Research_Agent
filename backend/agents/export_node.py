from backend.exporters.markdown_exporter import MarkdownExporter
from backend.exporters.pdf_exporter import PDFExporter
from backend.models.state import AgentState
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def export_node(state: AgentState) -> dict:
    query = state.get("query", "")
    summary = state.get("summary", {})
    raw_results = state.get("raw_results", [])

    if not summary:
        logger.warning("[ExportNode] No summary in state — skipping export")
        return {"export_paths": {}}

    metadata = {
        "tools_used": state.get("selected_tools", []),
        "iterations": state.get("iteration_count", 1),
        "sources_count": len(raw_results),
    }

    export_paths: dict[str, str] = {}

    try:
        md_path = MarkdownExporter().export(query, summary, raw_results, metadata)
        export_paths["markdown"] = md_path
        logger.info(f"[ExportNode] Markdown exported: {md_path}")
    except Exception as exc:
        logger.error(f"[ExportNode] Markdown export failed: {exc}")

    try:
        pdf_path = PDFExporter().export(query, summary, raw_results, metadata)
        export_paths["pdf"] = pdf_path
        logger.info(f"[ExportNode] PDF exported: {pdf_path}")
    except Exception as exc:
        logger.error(f"[ExportNode] PDF export failed: {exc}")

    return {"export_paths": export_paths}
