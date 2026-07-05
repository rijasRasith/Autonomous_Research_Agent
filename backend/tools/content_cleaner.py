# Content cleaner — Phase 9+10: normalizes raw tool results into a single clean corpus.
# Removes HTML artifacts, deduplicates paragraphs, and scores relevance.

import hashlib
import re
from typing import Optional

from backend.tools.base_tool import ToolResult
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Regex patterns for content that should be removed
_NOISE_PATTERNS: list[re.Pattern] = [
    re.compile(r"<[^>]+>"),                          # Leftover HTML tags
    re.compile(r"&[a-zA-Z]+;"),                       # HTML entities (&amp; &nbsp; etc.)
    re.compile(r"&#\d+;"),                            # Numeric HTML entities
    re.compile(r"\[[\d,\s]+\]"),                      # Wikipedia reference brackets [1][2]
    re.compile(r"https?://\S+"),                       # Bare URLs in text
    re.compile(r"={2,}|─{2,}|\*{3,}|-{3,}"),         # Repeated decoration chars
    re.compile(r"\s{3,}", re.MULTILINE),              # Excessive whitespace
    re.compile(r"^\s*(cookie|privacy policy|accept cookies|subscribe now|sign up)", re.I | re.M),
    re.compile(r"^\s*(menu|navigation|skip to|jump to|table of contents)", re.I | re.M),
]

# Minimum paragraph length to be considered meaningful
MIN_PARAGRAPH_LENGTH = 60

# Block-level HTML elements whose entire content should be wiped (tag + inner text + closing tag).
# These are stripped FIRST so their inner text doesn't bleed into adjacent paragraphs after cleanup.
_BLOCK_TAG_RE = re.compile(
    r"<(nav|header|footer|aside|script|style|noscript|form|button|svg|iframe)"
    r"[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)


def _clean_text(text: str) -> str:
    """Apply all noise-removal patterns while preserving paragraph boundaries."""
    # Step 0: wipe block-level tags (nav, header, etc.) WITH their inner content.
    # Replace with double-newline to maintain paragraph boundaries.
    text = _BLOCK_TAG_RE.sub("\n\n", text)

    # Step 1: protect paragraph separators (2+ newlines) before running noise patterns.
    # Noise patterns include \s{3,} which would otherwise collapse them.
    _PARA_SENTINEL = "\x00PARA\x00"
    text = re.sub(r"\n{2,}", _PARA_SENTINEL, text)

    # Step 2: strip remaining inline tags, entities, and other noise
    for pattern in _NOISE_PATTERNS:
        text = pattern.sub(" ", text)

    # Step 3: restore paragraph separators
    text = text.replace(_PARA_SENTINEL, "\n\n")

    # Step 4: normalize whitespace within each line (but not across paragraphs)
    paragraphs = text.split("\n\n")
    cleaned_paras: list[str] = []
    for para in paragraphs:
        lines = [" ".join(line.split()) for line in para.splitlines()]
        lines = [ln for ln in lines if len(ln) >= 20 or ln == ""]
        cleaned = " ".join(lines).strip()   # join lines within a paragraph into one line
        if cleaned:
            cleaned_paras.append(cleaned)

    return "\n\n".join(cleaned_paras).strip()


def _paragraph_hash(text: str) -> str:
    """Fingerprint a paragraph for deduplication (normalized lowercase)."""
    normalized = re.sub(r"\s+", " ", text.lower().strip())
    return hashlib.md5(normalized.encode()).hexdigest()


def clean_and_deduplicate(results: list[ToolResult]) -> tuple[str, list[dict]]:
    """
    Phase 9 + 10:
    1. Normalize every ToolResult's content into plain text.
    2. Split into paragraphs.
    3. Deduplicate by content hash.
    4. Filter out noise (nav, ads, cookie banners, etc.).
    5. Sort by relevance score (descending).
    6. Join into one clean corpus string.

    Returns:
        corpus (str): single clean text block ready for LLM analysis.
        cleaned_results (list[dict]): per-result dicts with cleaned content.
    """
    seen_hashes: set[str] = set()
    cleaned_results: list[dict] = []
    all_paragraphs: list[tuple[float, str, str]] = []  # (score, source_url, paragraph)

    for result in results:
        if result.error or not result.content:
            continue

        raw = result.content
        cleaned = _clean_text(raw)

        # Split into paragraphs (double-newline or single newline for short docs)
        paragraphs = re.split(r"\n{2,}", cleaned)
        if len(paragraphs) <= 1:
            paragraphs = cleaned.split("\n")

        good_paragraphs: list[str] = []
        for para in paragraphs:
            para = para.strip()
            if len(para) < MIN_PARAGRAPH_LENGTH:
                continue

            ph = _paragraph_hash(para)
            if ph in seen_hashes:
                continue  # Duplicate — skip

            seen_hashes.add(ph)
            good_paragraphs.append(para)
            all_paragraphs.append((result.relevance_score, result.url, para))

        if good_paragraphs:
            cleaned_result = result.to_dict()
            cleaned_result["content"] = "\n\n".join(good_paragraphs)
            cleaned_results.append(cleaned_result)

    if not cleaned_results:
        logger.warning("[ContentCleaner] No usable content after cleaning")
        return "", []

    # Sort paragraphs: higher relevance first, then by original order
    all_paragraphs.sort(key=lambda x: x[0], reverse=True)

    # Build final corpus with source annotations
    corpus_parts: list[str] = []
    for score, url, para in all_paragraphs:
        corpus_parts.append(para)

    corpus = "\n\n---\n\n".join(corpus_parts)

    logger.info(
        f"[ContentCleaner] Cleaned corpus | "
        f"sources={len(cleaned_results)} | "
        f"paragraphs={len(all_paragraphs)} | "
        f"chars={len(corpus)}"
    )

    return corpus, cleaned_results
