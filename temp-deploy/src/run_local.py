import logging
import sys

# Configure clean logging format matching your pipeline tracing
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Import your compiled multi-agent execution framework
from agentcore.src.orchestrator.graph import compiled_graph


def get_slot(final_state, field_name: str) -> dict:
    """Safely extracts a state slot whether the return object is a dict or Pydantic model."""
    if hasattr(final_state, field_name):
        val = getattr(final_state, field_name)
    elif isinstance(final_state, dict):
        val = final_state.get(field_name, {})
    else:
        val = {}
    return val if val is not None else {}


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RUNNING FULL 5-AGENT PARALLEL FAN-OUT ORCHESTRATION (ZONE 4)")
    print("=" * 60)

    # Inbound orchestration configuration fields matching OrchestratorState
    initial_inputs = {
        "run_id": "orchestration_live_tesla_001",
        "company": "Tesla",  # Changing this forces a fresh live API pull!
        "country": "US",
        "tier": "Premium",
    }

    try:
        # Run the LangGraph state machine workflow to completion
        final_state = compiled_graph.invoke(initial_inputs)

        print("\n" + "=" * 60)
        print("SYNCHRONIZATION BARRIER COMPLETE: MASTER CONSOLIDATED STATE")
        print("=" * 60)

        # Parse data out of the completed synchronization barrier state
        research_data = get_slot(final_state, "research")
        financial_data = get_slot(final_state, "financial")
        news_data = get_slot(final_state, "news")
        leadership_data = get_slot(final_state, "leadership")
        litigation_data = get_slot(final_state, "litigation")

        # Display formatted execution metrics to console terminal
        print(f"\n [Research Slot]   -> {research_data.get('profile', {}).get('summary', 'No summary found')}")
        print(f" [Financial Slot]  -> Ticker: {financial_data.get('ticker')}, Price: {financial_data.get('share_price')}, Growth (CAGR): {financial_data.get('cagr_5y') or 0.0}%, Cache Hit: {financial_data.get('cache_hit')}") 
        print(f" [News Slot]       -> Sent: {news_data.get('sentiment_score', 0.0)}, Headlines Count: {len(news_data.get('recent_headlines', []))}")
        print(f" [Leadership Slot] -> Exec Updates Count: {len(leadership_data.get('executives_updates', []))}, Product Lines Count: {len(leadership_data.get('product_lines_updates', []))}")
        print(f"  [Litigation Slot]-> Active Court Cases: {litigation_data.get('active_count', 0)}")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n Orchestration Graph execution failed: {e}", file=sys.stderr)