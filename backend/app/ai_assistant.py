"""Opt-in Gemini explanation of fictional aggregate facts, with local fallback."""
import json
import os
from typing import TypedDict

from google import genai
from google.genai import types
from langgraph.graph import START, END, StateGraph
from langsmith import tracing_context

CATEGORIES = frozenset(("Mobile recharge", "Electricity", "Water", "Gas",
                        "Internet", "Peer payments", "Other services", "Other"))
TOPICS = frozenset(("spending", "budget", "savings", "risk"))
PROMPT = (
    "You are ARTH's educational demo assistant. The input is fictional aggregate "
    "finance data, in integer INR paise. Explain the selected topic in at most "
    "three short sentences. Give practical budgeting or review suggestions, not "
    "investment advice, credit recommendations, guarantees or fraud verdicts. "
    "Do not invent figures or personal details. Do not ask for credentials. "
    "Do not perform or propose to execute any transaction. No tools are available. "
    "The authoritative numerical facts appear separately in the app."
)

def number(value):
    return value if type(value) is int else None

def aggregate(topic, facts):
    """Allowlist only fixed labels and numeric aggregates; never pass user text."""
    if topic == "spending":
        return {"spent_minor": number(facts["spent_minor"]),
                "categories": [{"category": r["category"], "amount_minor": number(r["amount_minor"])}
                               for r in facts["categories"] if r["category"] in CATEGORIES]}
    if topic == "budget":
        return {k: number(facts[k]) for k in ("limit_minor", "remaining_minor")}
    if topic == "savings":
        return {k: number(facts[k]) for k in ("target_minor", "saved_minor", "remaining_minor")}
    if topic == "risk":
        return {"review_flag_count": len(facts["flags"]), "fraud_confirmed": False}
    raise ValueError("Unsupported assistant topic")

def configured():
    return (os.getenv("ARTH_AI_ENABLED") == "1" and
            bool(os.getenv("ARTH_GEMINI_API_KEY", "").strip()) and
            bool(os.getenv("ARTH_GEMINI_MODEL", "").strip()))

def generate(topic, facts):
    # No ambient key, user-supplied endpoint, tool access or persistent chat.
    with genai.Client(api_key=os.environ["ARTH_GEMINI_API_KEY"],
                      vertexai=False,
                      http_options=types.HttpOptions(
                          timeout=5000, retry_options=types.HttpRetryOptions(attempts=1))) as client:
        response = client.models.generate_content(
            model=os.environ["ARTH_GEMINI_MODEL"],
            contents=json.dumps({"topic": topic, "demo_aggregates": facts}, ensure_ascii=True),
            config=types.GenerateContentConfig(system_instruction=PROMPT,
                                               max_output_tokens=512, temperature=0.2))
        return (response.text or "").strip()

class AssistantState(TypedDict, total=False):
    topic: str
    facts: dict
    consent: bool
    engine: str
    explanation: str | None
    fallback_reason: str | None

def choose(state):
    return "provider" if state["consent"] and configured() else "local"

def local(state):
    return {"engine": "deterministic rules", "explanation": None,
            "fallback_reason": "provider_unconfigured" if state["consent"] else "local_selected"}

def provider(state):
    try:
        answer = generate(state["topic"], state["facts"])
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Empty provider result")
        # Treat output as untrusted display text, never executable instructions.
        return {"engine": "gemini", "explanation": answer.strip()[:1800], "fallback_reason": None}
    except Exception:
        # Do not return exception contents, provider payloads or secrets.
        return {"engine": "deterministic rules", "explanation": None,
                "fallback_reason": "provider_unavailable"}

builder = StateGraph(AssistantState)
builder.add_node("local", local)
builder.add_node("provider", provider)
builder.add_conditional_edges(START, choose, {"local": "local", "provider": "provider"})
builder.add_edge("local", END)
builder.add_edge("provider", END)
graph = builder.compile()

def explain(topic, facts, consent=False):
    if topic not in TOPICS:
        raise ValueError("Unsupported topic")
    # Never put raw ledger facts, user text or credentials in graph state.
    with tracing_context(enabled=False):
        result = graph.invoke({"topic": topic, "facts": aggregate(topic, facts), "consent": consent})
    return {k: result[k] for k in ("engine", "explanation", "fallback_reason")}
