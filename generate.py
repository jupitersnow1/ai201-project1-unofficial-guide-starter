"""
Milestone 5 — Grounded Generation and Interface

This is the final stage of the RAG pipeline. It:

  1. Retrieves the top-k chunks for a question (from vector_store.py).
  2. Builds a prompt that puts those chunks in front of the model as CONTEXT.
  3. Asks a Groq-hosted LLM to answer using ONLY that context (grounding), and
     to say "I don't know based on the provided sources" when the context
     doesn't contain the answer.
  4. Returns the answer plus the source files it drew from.

Run:
  python generate.py            # launch the Gradio web interface
  python generate.py --test     # run a few questions in the terminal (incl. an
                                 # off-topic one to prove grounding works)

Requires a GROQ_API_KEY in your .env file (copy .env.example to .env first).
"""

import os
import sys

from dotenv import load_dotenv
from groq import Groq

from vector_store import retrieve, TOP_K

load_dotenv()  # read GROQ_API_KEY from .env

# A capable, fast Groq-hosted model. If Groq deprecates it, swap for another
# from https://console.groq.com/docs/models (e.g. "llama-3.1-8b-instant").
GROQ_MODEL = "llama-3.3-70b-versatile"

# The grounding instruction. This is what stops the model from answering from
# its own training data instead of from the retrieved documents.
SYSTEM_PROMPT = """You are an assistant that answers questions about software development best practices.

Follow these rules strictly:
- Answer using ONLY the information in the CONTEXT provided in the user's message.
- If the context does not contain enough information to answer the question, reply with exactly: "I don't know based on the provided sources."
- Do NOT use any outside or prior knowledge, and do not guess or invent details.
- Keep the answer concise and accurate.
- End your answer with a "Sources:" line listing the source file name(s) you actually used."""

_client = None


def _get_client() -> Groq:
    """Create the Groq client lazily so importing this module needs no API key."""
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key or api_key == "your_key_here":
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = Groq(api_key=api_key)
    return _client


def _format_context(hits: list[dict]) -> str:
    """Lay out retrieved chunks with a clear source label before each one."""
    blocks = []
    for hit in hits:
        blocks.append(f"[Source: {hit['source']}]\n{hit['text']}")
    return "\n\n---\n\n".join(blocks)


def answer_question(query: str, top_k: int = TOP_K) -> dict:
    """
    Run the full RAG flow for one question.

    Returns {"answer": str, "sources": list[str], "hits": list[dict]}.
    """
    hits = retrieve(query, top_k=top_k)
    context = _format_context(hits)

    response = _get_client().chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,  # deterministic, factual answers
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}"},
        ],
    )
    answer = response.choices[0].message.content.strip()

    # Unique source files behind the retrieved chunks (for display/attribution).
    sources = list(dict.fromkeys(hit["source"] for hit in hits))
    return {"answer": answer, "sources": sources, "hits": hits}


# ---------------------------------------------------------------------------
# Gradio interface
# ---------------------------------------------------------------------------

def _ask_ui(query: str):
    """Adapter for Gradio: returns (answer_markdown, retrieved_chunks_markdown)."""
    if not query.strip():
        return "Please enter a question.", ""
    result = answer_question(query)

    # Show what was retrieved, so it's clear the answer is grounded in real chunks.
    retrieved = []
    for i, hit in enumerate(result["hits"], 1):
        preview = hit["text"].replace("\n", " ")[:200]
        retrieved.append(f"**{i}. {hit['source']}** (score {hit['score']:.3f})\n\n> {preview}...")
    return result["answer"], "\n\n".join(retrieved)


def build_interface():
    import gradio as gr

    with gr.Blocks(title="The Unofficial Guide — Software Dev Best Practices") as demo:
        gr.Markdown(
            "# The Unofficial Guide\n"
            "Ask about software development best practices. Answers are grounded "
            "**only** in the 10 collected sources — if the answer isn't in them, "
            "the system says so."
        )
        question = gr.Textbox(label="Your question", placeholder="e.g. What are the four quadrants of Fowler's technical debt?")
        ask = gr.Button("Ask", variant="primary")
        answer = gr.Markdown(label="Answer")
        with gr.Accordion("Retrieved chunks (the grounding)", open=False):
            retrieved = gr.Markdown()

        ask.click(_ask_ui, inputs=question, outputs=[answer, retrieved])
        question.submit(_ask_ui, inputs=question, outputs=[answer, retrieved])

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _print_answer(query: str) -> None:
    result = answer_question(query)
    print("\n" + result["answer"])
    print("\nSources used:", ", ".join(result["sources"]) or "(none)")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--test" in args:
        # Quick grounding check: in-domain questions should answer with sources;
        # the off-topic question should be refused.
        tests = [
            # The five evaluation questions from planning.md
            "What does the 'S' in SOLID stand for, and what does it mean?",
            "What are the four quadrants of Martin Fowler's Technical Debt Quadrant?",
            "What are the three steps of the Test-Driven Development cycle?",
            "What is the structure of a Conventional Commit message?",
            "What standard should a reviewer use when deciding to approve a code change?",
            # The design-pattern question that exposed (and now confirms the fix for)
            # the SourceMaking coverage gap
            "What problem does the Observer pattern solve?",
            # Off-topic question -> the system must refuse (grounding check)
            "What is the best topping for a pizza?",
        ]
        for q in tests:
            print("\n" + "=" * 80)
            print("Q:", q)
            _print_answer(q)

    elif "--cli" in args:
        # Interactive terminal: type your own questions, one at a time.
        print("Ask questions about software development best practices.")
        print("Type 'quit' (or press Ctrl+C) to stop.")
        while True:
            try:
                q = input("\nQuestion> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not q:
                continue
            if q.lower() in {"quit", "exit", "q"}:
                break
            print("=" * 60)
            _print_answer(q)
            print("=" * 60)

    elif "--ask" in args:
        # One-shot: everything after --ask is treated as the question.
        question = " ".join(args[args.index("--ask") + 1:]).strip()
        if not question:
            print('Usage: python generate.py --ask "your question here"')
        else:
            _print_answer(question)

    else:
        build_interface().launch()
