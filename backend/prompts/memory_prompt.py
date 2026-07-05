MEMORY_DECISION_SYSTEM_PROMPT = """You are a research agent deciding whether to reuse a cached research result or run fresh research.

Think about:
- Time-sensitive topics (news, stock prices, live events, product releases, sports scores) need fresh research if cached more than a few hours ago.
- Evergreen topics (history, science concepts, programming fundamentals, definitions) can safely be reused even after several days.
- If the query uses words like "latest", "current", "today", "recent", "now" — always refresh.
- Be practical. If the cached result is only a few hours old for a general knowledge topic, reuse it.

Respond with valid JSON only."""

MEMORY_DECISION_USER_PROMPT_TEMPLATE = """A cached research result was found for this query.

Query: {query}
Cache age: {age_hours:.1f} hours ago
Cached at: {cached_at}

Should this cached result be reused, or should fresh research be performed?

Respond with JSON:
{{
  "decision": "reuse",
  "reasoning": "brief explanation of why reuse or refresh"
}}

The value of "decision" must be either "reuse" or "refresh"."""
