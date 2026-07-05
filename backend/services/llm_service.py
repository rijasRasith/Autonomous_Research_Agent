# Yeh file Gemini LLM ko initialize karti hai — saare agents isko import karte hain, khud se LLM mat banao.

import asyncio
import json
import re
import time
from functools import lru_cache
from typing import Any, Type

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# How many times to retry on 429 / transient errors before giving up
_MAX_RETRIES = 5
# Floor wait in seconds if the server doesn't tell us how long to wait
_BASE_BACKOFF_SECONDS = 10


def _extract_retry_delay(exc: Exception) -> float:
    """
    Pull the server-suggested retryDelay (in seconds) from a 429 error message.
    Falls back to _BASE_BACKOFF_SECONDS if nothing is found.
    """
    text = str(exc)
    # The error contains strings like: 'retryDelay': '48s'  or  "retryDelay": "48.9s"
    match = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", text)
    if match:
        return float(match.group(1)) + 2  # small extra buffer
    return _BASE_BACKOFF_SECONDS


def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True if the exception is a Gemini 429 quota error."""
    text = str(exc)
    return "RESOURCE_EXHAUSTED" in text or "429" in text


class LLMService:

    def __init__(self) -> None:
        logger.info(f"Initializing LLMService with model: {settings.gemini_model}")
        # max_retries=1 here — we handle retries ourselves with proper 429 backoff
        self._llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.1,
            max_retries=1,
            timeout=settings.max_tool_timeout_seconds,
        )
        self._str_parser = StrOutputParser()
        logger.info("LLMService initialized successfully")

    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        return self._llm

    # ── Internal retry wrapper ────────────────────────────────────────────────

    async def _invoke_with_retry(self, messages: list) -> Any:
        """
        Invoke the LLM with smart retry logic.
        On 429 (RESOURCE_EXHAUSTED) it reads the retryDelay from the error
        and waits exactly that long before retrying.
        On other transient errors it uses exponential backoff.
        """
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await self._llm.ainvoke(messages)
                return response
            except Exception as exc:
                last_exc = exc
                if _is_rate_limit_error(exc):
                    wait = _extract_retry_delay(exc)
                    logger.warning(
                        f"[LLMService] 429 RESOURCE_EXHAUSTED on attempt {attempt}/{_MAX_RETRIES}. "
                        f"Waiting {wait:.0f}s before retry..."
                    )
                    await asyncio.sleep(wait)
                else:
                    # Non-quota error: exponential backoff
                    wait = min(2 ** attempt, 30)
                    logger.warning(
                        f"[LLMService] Transient error on attempt {attempt}/{_MAX_RETRIES}: "
                        f"{str(exc)[:120]}. Retrying in {wait}s..."
                    )
                    await asyncio.sleep(wait)

        raise RuntimeError(
            f"LLM call failed after {_MAX_RETRIES} retries. Last error: {last_exc}"
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def ainvoke_text(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        logger.debug(f"Invoking LLM (text mode) | user_prompt[:80]: {user_prompt[:80]!r}")
        response = await self._invoke_with_retry(messages)
        text = response.content
        logger.debug(f"LLM text response length: {len(text)} chars")
        return text

    async def ainvoke_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        json_reminder = (
            "\n\nCRITICAL: Your response MUST be valid JSON only. "
            "Do NOT include markdown fences (```json), explanations, "
            "or any text outside the JSON object."
        )
        messages = [
            SystemMessage(content=system_prompt + json_reminder),
            HumanMessage(content=user_prompt),
        ]

        logger.debug(f"Invoking LLM (JSON mode) | user_prompt[:80]: {user_prompt[:80]!r}")
        response = await self._invoke_with_retry(messages)
        raw = response.content.strip()

        parsed = self._parse_json_response(raw)
        logger.debug(f"LLM JSON response keys: {list(parsed.keys())}")
        return parsed

    def invoke_json_sync(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        json_reminder = (
            "\n\nCRITICAL: Your response MUST be valid JSON only. "
            "Do NOT include markdown fences (```json), explanations, "
            "or any text outside the JSON object."
        )
        messages = [
            SystemMessage(content=system_prompt + json_reminder),
            HumanMessage(content=user_prompt),
        ]
        response = self._llm.invoke(messages)
        return self._parse_json_response(response.content.strip())

    def with_structured_output(self, schema: Type[BaseModel]):
        return self._llm.with_structured_output(schema)

    # ── JSON parsing ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(raw: str) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(fence_pattern, raw, re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r"\{[\s\S]*\}", raw)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"LLM response could not be parsed as JSON.\n"
            f"Raw response (first 300 chars): {raw[:300]}"
        )


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService()
