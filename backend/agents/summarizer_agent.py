# Yeh file summarizer agent hai — collected data lekar LLM se final structured research report banwata hai.

from backend.models.state import AgentState
from backend.prompts.summarizer_prompt import (
    SUMMARIZER_SYSTEM_PROMPT,
    SUMMARIZER_USER_PROMPT_TEMPLATE,
)
from backend.services.llm_service import get_llm_service
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def summarizer_node(state: AgentState) -> dict:
    query = state.get("query", "")
    plan = state.get("research_plan", {})
    corpus = state.get("cleaned_corpus", "")
    raw_results = state.get("raw_results", [])

    logger.info(
        f"[SummarizerAgent] Generating report | "
        f"corpus_chars={len(corpus)} | sources={len(raw_results)}"
    )

    if not corpus.strip():
        logger.warning("[SummarizerAgent] Empty corpus — returning minimal summary")
        return {
            "summary": {
                "executive_summary": f"No research data was collected for the query: {query}",
                "key_points": ["No data collected"],
                "important_findings": [],
                "references": [],
                "actionable_insights": ["Try rephrasing the query or checking API keys"],
            }
        }

    llm = get_llm_service()

    user_prompt = SUMMARIZER_USER_PROMPT_TEMPLATE.format(
        query=query,
        goal=plan.get("goal", query),
        corpus=corpus,
    )

    try:
        summary = await llm.ainvoke_json(
            system_prompt=SUMMARIZER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        logger.info(
            f"[SummarizerAgent] Report generated | "
            f"key_points={len(summary.get('key_points', []))} | "
            f"references={len(summary.get('references', []))}"
        )
        return {"summary": summary}

    except Exception as exc:
        logger.error(f"[SummarizerAgent] Failed: {exc}")
        return {
            "summary": {
                "executive_summary": f"Research completed for: {query}. Summary generation encountered an error.",
                "key_points": ["Summary generation failed — raw data was collected"],
                "important_findings": [],
                "references": [
                    {"title": r.get("query", ""), "url": r.get("url", ""), "relevance": "Collected source"}
                    for r in raw_results[:5]
                ],
                "actionable_insights": ["Review the raw corpus for detailed information"],
            }
        }
