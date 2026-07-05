# GitHub Tool — searches GitHub repositories, README files, and code using the public GitHub REST API.

import asyncio
import base64

import aiohttp

from backend.tools.base_tool import BaseTool, ToolResult
from backend.utils.logger import get_logger

logger = get_logger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "AutonomousResearchAgent/1.0",
    "X-GitHub-Api-Version": "2022-11-28",
}


class GitHubTool(BaseTool):
    """Search GitHub for relevant repositories and read their README content."""

    name = "github"
    description = "Search GitHub for open-source projects, documentation, and code examples."

    async def run(self, query: str, max_results: int = 4) -> list[ToolResult]:
        logger.info(f"[GitHubTool] Searching: {query!r}")
        try:
            repos = await self._search_repos(query, max_results)
            if not repos:
                logger.warning(f"[GitHubTool] No repos found for: {query!r}")
                return []

            # Fetch README for each repo concurrently (top 3 only to stay fast)
            tasks = [self._get_readme(repo, query) for repo in repos[:3]]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            good = [r for r in results if isinstance(r, ToolResult) and not r.error]
            logger.info(f"[GitHubTool] Got {len(good)} repo READMEs for: {query!r}")
            return good

        except Exception as exc:
            logger.error(f"[GitHubTool] Error for {query!r}: {exc}")
            return [ToolResult(
                tool=self.name, query=query,
                title="[Error] GitHub search failed",
                content="", url="", error=str(exc)
            )]

    async def _search_repos(self, query: str, limit: int) -> list[dict]:
        # Extract short keyword query — GitHub API performs poorly on long natural-language strings
        keywords = self._extract_keywords(query)
        logger.info(f"[GitHubTool] Keyword query: {keywords!r} (from: {query[:60]!r})")

        url = f"{GITHUB_API}/search/repositories"
        params = {
            "q": keywords,
            "sort": "stars",
            "order": "desc",
            "per_page": limit,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers=GITHUB_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 403:
                    logger.warning("[GitHubTool] Rate limited by GitHub API")
                    return []
                data = await resp.json()
                return data.get("items", [])

    @staticmethod
    def _extract_keywords(query: str) -> str:
        """
        Extract a compact keyword string suitable for GitHub search.
        Strips question words, prepositions, year references, and other stop words
        that reduce GitHub search effectiveness.
        """
        import re
        # Remove common question/sentence prefixes
        query = re.sub(
            r"^(what|how|why|when|where|which|who|are|is|can|do|does|tell me about|explain|describe)\s+",
            "",
            query.strip(),
            flags=re.IGNORECASE,
        )
        # Remove stop words and filler
        stop_words = {
            "the", "a", "an", "and", "or", "for", "in", "of", "to", "with",
            "on", "at", "by", "from", "that", "this", "it", "its", "be", "been",
            "used", "using", "use", "best", "top", "good", "great", "better",
            "specifically", "including", "about", "between", "trends", "future",
        }
        words = re.findall(r"\b\w+\b", query)
        # Drop stop words and very short words, keep numbers that look like years
        keywords = [
            w for w in words
            if w.lower() not in stop_words and (len(w) > 2 or w.isdigit())
        ]
        # Cap at 6 keywords to stay within GitHub's effective search length
        return " ".join(keywords[:6])


    async def _get_readme(self, repo: dict, query: str) -> ToolResult:
        full_name = repo.get("full_name", "")
        html_url = repo.get("html_url", "")
        stars = repo.get("stargazers_count", 0)
        description = repo.get("description") or ""

        url = f"{GITHUB_API}/repos/{full_name}/readme"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=GITHUB_HEADERS,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    # Fall back to just using the repo description
                    content = f"Repository: {full_name}\nDescription: {description}\nStars: {stars:,}"
                    return ToolResult(
                        tool=self.name,
                        query=query,
                        title=f"GitHub: {full_name} ⭐ {stars:,}",
                        content=content,
                        url=html_url,
                        source_type="github",
                        relevance_score=0.6,
                    )
                data = await resp.json()

        # README content is base64-encoded
        encoded = data.get("content", "")
        try:
            raw = base64.b64decode(encoded).decode("utf-8", errors="replace")
        except Exception:
            raw = description

        # Strip excessive blank lines and truncate
        lines = [l for l in raw.splitlines() if l.strip()]
        readme_text = "\n".join(lines[:60])  # first 60 meaningful lines
        if len(readme_text) > 2500:
            readme_text = readme_text[:2500].rsplit(" ", 1)[0] + "..."

        content = (
            f"Repository: {full_name} | Stars: {stars:,}\n"
            f"Description: {description}\n\n"
            f"README:\n{readme_text}"
        )

        return ToolResult(
            tool=self.name,
            query=query,
            title=f"GitHub: {full_name} ⭐ {stars:,}",
            content=content,
            url=html_url,
            source_type="github",
            relevance_score=min(1.0, 0.5 + stars / 100_000),
        )
