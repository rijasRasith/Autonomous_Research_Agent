"""End-to-end agent graph test — runs the full Plan -> Search -> Reflect -> Summarize loop."""
import asyncio
import json
from backend.graph.research_graph import get_research_graph

async def test():
    print("=" * 60)
    print("Full LangGraph Agent Pipeline Test")
    print("=" * 60)
    graph = get_research_graph()
    result = await graph.ainvoke({
        "query": "What is LangGraph and how does it enable autonomous AI agents?",
        "raw_results": [],
        "warnings": [],
    })

    print(f"\nIterations ran:     {result.get('iteration_count', '?')}")
    print(f"Tools selected:     {result.get('selected_tools', [])}")
    print(f"Sources collected:  {len(result.get('raw_results', []))}")
    print(f"Corpus chars:       {len(result.get('cleaned_corpus', ''))}")

    summary = result.get("summary", {})
    print("\n--- SUMMARY ---")
    print("Executive Summary:")
    print(summary.get("executive_summary", "N/A")[:400])
    print("\nKey Points:")
    for kp in summary.get("key_points", [])[:3]:
        print(f"  • {kp}")
    print("\nActionable Insights:")
    for ai in summary.get("actionable_insights", [])[:2]:
        print(f"  → {ai}")
    print("\nReferences:")
    for ref in summary.get("references", [])[:3]:
        title = ref.get("title", "") if isinstance(ref, dict) else str(ref)
        url = ref.get("url", "") if isinstance(ref, dict) else ""
        print(f"  [{title[:50]}] {url[:60]}")

asyncio.run(test())
