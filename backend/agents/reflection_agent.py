# Yeh file reflection agent hai — LLM decide karta hai ki ab aur search karna hai ya report banana shuru kar do.

from backend.models.state import AgentState
from backend.prompts.reflection_prompt import (
    REFLECTION_SYSTEM_PROMPT,
    REFLECTION_USER_PROMPT_TEMPLATE,
)
from backend.services.llm_service import get_llm_service
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_CORPUS_PREVIEW_CHARS = 3000


async def reflection_node(state: AgentState) -> dict:
    query = state.get("query", "")
    plan = state.get("research_plan", {})
    raw_results = state.get("raw_results", [])
    corpus = state.get("cleaned_corpus", "")
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 3)

    logger.info(
        f"[ReflectionAgent] Evaluating iteration {iteration + 1}/{max_iter} | "
        f"sources={len(raw_results)} | corpus_chars={len(corpus)}"
    )

    if iteration >= max_iter - 1:
        logger.warning(
            f"[ReflectionAgent] Max iterations ({max_iter}) reached — forcing completion"
        )
        return {
            "reflection": {
                "is_sufficient": True,
                "confidence_score": 0.75,
                "missing_information": [],
                "additional_queries": [],
                "reasoning": f"Maximum iterations ({max_iter}) reached. Proceeding with available data.",
            },
            "iteration_count": iteration + 1,
        }

    llm = get_llm_service()

    corpus_preview = corpus[:_CORPUS_PREVIEW_CHARS]
    if len(corpus) > _CORPUS_PREVIEW_CHARS:
        corpus_preview += f"\n... [truncated, {len(corpus)} chars total]"

    required_info = "\n".join(
        f"- {item}" for item in plan.get("required_information", [query])
    )

    user_prompt = REFLECTION_USER_PROMPT_TEMPLATE.format(
        query=query,
        goal=plan.get("goal", query),
        required_information=required_info,
        corpus_summary=corpus_preview,
        source_count=len(raw_results),
        iteration=iteration + 1,
        max_iterations=max_iter,
    )

    try:
        reflection = await llm.ainvoke_json(
            system_prompt=REFLECTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        is_sufficient = reflection.get("is_sufficient", False)
        confidence = reflection.get("confidence_score", 0.0)

        logger.info(
            f"[ReflectionAgent] Decision: {'SUFFICIENT' if is_sufficient else 'NEEDS MORE RESEARCH'} | "
            f"confidence={confidence:.2f} | "
            f"additional_queries={len(reflection.get('additional_queries', []))}"
        )

        return {
            "reflection": reflection,
            "iteration_count": iteration + 1,
        }

    except Exception as exc:
        logger.error(f"[ReflectionAgent] Failed: {exc} — defaulting to sufficient")
        return {
            "reflection": {
                "is_sufficient": True,
                "confidence_score": 0.6,
                "missing_information": [],
                "additional_queries": [],
                "reasoning": f"Reflection failed ({exc}), proceeding with available data.",
            },
            "iteration_count": iteration + 1,
        }
