"""
Milestone 3 — Document Ingestion and Chunking

This module does the first two stages of the RAG pipeline:

  1. Document Ingestion: read every file in documents/ and pull out clean text.
       - PDFs are read with pdfplumber.
       - .txt / .md files are read directly.
       - .html files have their tags stripped out.

  2. Chunking: split each document's text into overlapping 256-token chunks.
       Chunk size and overlap match the planning.md decision (256 / 50) and the
       all-MiniLM-L6-v2 model's 256-token maximum, so nothing is truncated when
       we embed later in Milestone 4.

Run this file directly (`python ingest.py`) to ingest documents/ and print
statistics so you can sanity-check the chunks before building the vector store.
"""

import re
from pathlib import Path

import pdfplumber
from transformers import AutoTokenizer

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DOCUMENTS_DIR = Path(__file__).parent / "documents"

# These two numbers come straight from planning.md (Chunking Strategy).
CHUNK_SIZE = 256     # tokens per chunk — matches the embedding model's max length
CHUNK_OVERLAP = 50   # tokens shared between neighboring chunks

# We count tokens with the SAME tokenizer the embedding model uses, so "256
# tokens" here means exactly what the model will see in Milestone 4. Loading it
# once at import time avoids re-loading it on every call.
_TOKENIZER = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")


# ---------------------------------------------------------------------------
# Stage 1: Document Ingestion
# ---------------------------------------------------------------------------

def _read_pdf(path: Path) -> str:
    """
    Extract text from a PDF, one page at a time, and join the pages.

    We call dedupe_chars() before extracting because PDFs often render **bold**
    text by drawing each glyph twice with a tiny offset. Without this, bold words
    come out with doubled characters (e.g. "Dollar" -> "DDoollllaarr"), which
    badly pollutes code-heavy documents. dedupe_chars() drops the overprinted
    duplicates so the text reads normally.
    """
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.dedupe_chars().extract_text() or ""  # can return None
            pages.append(text)
    return "\n".join(pages)


def _read_html(path: Path) -> str:
    """Very light HTML-to-text: drop script/style blocks, then strip tags."""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", " ", raw)          # remove remaining tags
    return raw


def _clean_text(text: str) -> str:
    """Collapse runs of whitespace/blank lines that hurt chunk quality."""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)         # collapse spaces/tabs
    text = re.sub(r"\n{3,}", "\n\n", text)      # collapse big blank-line gaps
    return text.strip()


def load_documents(documents_dir: Path = DOCUMENTS_DIR) -> list[dict]:
    """
    Read every supported file in `documents_dir`.

    Returns a list of dicts: {"source": <filename>, "text": <clean text>}.
    The "source" is kept so we can attribute answers to documents later.
    """
    documents = []
    for path in sorted(documents_dir.iterdir()):
        if path.name.startswith(".") or not path.is_file():
            continue  # skip .gitkeep and hidden files

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text = _read_pdf(path)
        elif suffix in {".txt", ".md"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
        elif suffix in {".html", ".htm"}:
            text = _read_html(path)
        else:
            print(f"  (skipping unsupported file type: {path.name})")
            continue

        text = _clean_text(text)
        if text:
            documents.append({"source": path.name, "text": text})
        else:
            print(f"  (warning: no text extracted from {path.name})")

    return documents


# ---------------------------------------------------------------------------
# Stage 2: Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split `text` into overlapping chunks measured in model tokens.

    A sliding window of `chunk_size` tokens moves forward by
    (chunk_size - overlap) tokens each step, so consecutive chunks share
    `overlap` tokens of context.

    We tokenize only to find WHERE to cut, then slice the ORIGINAL text by
    character offsets. This keeps each chunk's real capitalization and
    punctuation (important for readable source citations) instead of the
    lowercased, normalized text we'd get by decoding token ids back to a string.
    """
    # offset_mapping gives the (start_char, end_char) span of every token in the
    # original string. add_special_tokens=False keeps the windows pure content.
    encoding = _TOKENIZER(text, add_special_tokens=False, return_offsets_mapping=True)
    offsets = encoding["offset_mapping"]

    if not offsets:
        return []

    step = chunk_size - overlap
    chunks = []
    for start in range(0, len(offsets), step):
        window = offsets[start:start + chunk_size]
        char_start = window[0][0]      # first char of the first token in the window
        char_end = window[-1][1]       # last char of the last token in the window
        chunk = text[char_start:char_end].strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(offsets):
            break  # we've covered the end of the document
    return chunks


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Turn a list of documents into a flat list of chunk records.

    Each record: {"source": <filename>, "chunk_index": <int>, "text": <chunk>}.
    This is the shape we'll hand to the vector store in Milestone 4.
    """
    records = []
    for doc in documents:
        for i, chunk in enumerate(chunk_text(doc["text"])):
            records.append({
                "source": doc["source"],
                "chunk_index": i,
                "text": chunk,
            })
    return records


# ---------------------------------------------------------------------------
# Run directly to ingest documents/ and print sanity-check statistics.
# ---------------------------------------------------------------------------

def _count_tokens(text: str) -> int:
    return len(_TOKENIZER.encode(text, add_special_tokens=False))


if __name__ == "__main__":
    print(f"Loading documents from: {DOCUMENTS_DIR}")
    docs = load_documents()
    print(f"Loaded {len(docs)} document(s).\n")

    if not docs:
        print("documents/ is empty. Add your source files and run again.")
        raise SystemExit(0)

    chunks = chunk_documents(docs)
    print(f"Produced {len(chunks)} chunk(s) total.\n")

    # Per-document breakdown so one oversized source is easy to spot
    # (this is the "one source dominating retrieval" risk from planning.md).
    print("Chunks per source:")
    for doc in docs:
        n = sum(1 for c in chunks if c["source"] == doc["source"])
        print(f"  {n:4d}  {doc['source']}")

    # Token-length stats: every chunk should be <= 256 tokens (no truncation).
    lengths = [_count_tokens(c["text"]) for c in chunks]
    print(f"\nChunk token lengths -> min {min(lengths)}, "
          f"max {max(lengths)}, avg {sum(lengths) // len(lengths)}")

    # Show that consecutive chunks actually overlap.
    if len(chunks) >= 2:
        print("\n--- Sample: end of chunk 0 vs. start of chunk 1 (should overlap) ---")
        print("chunk 0 (last 120 chars): ..." + chunks[0]["text"][-120:])
        print("chunk 1 (first 120 chars): " + chunks[1]["text"][:120] + "...")
