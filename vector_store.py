"""
Milestone 4 — Embedding, Vector Store, and Retrieval

This module does stages 3 and 4 of the RAG pipeline:

  3. Embedding + Vector Store: take the chunks from ingest.py, turn each one
     into a 384-dimension vector with all-MiniLM-L6-v2, and store the vectors
     (plus their text and source) in a persistent ChromaDB collection.

  4. Retrieval: embed a user's question the same way and ask ChromaDB for the
     `top_k` most similar chunks.

Run `python vector_store.py` to (re)build the index and run a quick retrieval
test against the evaluation questions from planning.md.
"""

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from ingest import load_documents, chunk_documents

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_NAME = "all-MiniLM-L6-v2"          # matches the Chunking Strategy (256-token limit)
TOP_K = 4                                 # from planning.md Retrieval Approach
PERSIST_DIR = str(Path(__file__).parent / "chroma_db")  # gitignored local storage
COLLECTION_NAME = "software_best_practices"

# Load the embedding model once. SentenceTransformer downloads it on first use
# and caches it afterward.
_MODEL = SentenceTransformer(MODEL_NAME)


def _embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts into normalized vectors (good for cosine similarity)."""
    vectors = _MODEL.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def _get_client() -> chromadb.ClientAPI:
    """A PersistentClient writes the index to disk so we don't re-embed every run."""
    return chromadb.PersistentClient(path=PERSIST_DIR)


# ---------------------------------------------------------------------------
# Stage 3: Build the vector store
# ---------------------------------------------------------------------------

def build_index() -> int:
    """
    Load + chunk all documents, embed every chunk, and (re)build the ChromaDB
    collection from scratch. Returns the number of chunks indexed.
    """
    docs = load_documents()
    chunks = chunk_documents(docs)
    if not chunks:
        raise SystemExit("No chunks to index — is documents/ empty?")

    client = _get_client()
    # Start fresh each build so re-running never creates duplicates.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # collection didn't exist yet
    # cosine space pairs with our normalized embeddings.
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    texts = [c["text"] for c in chunks]
    # A unique id per chunk, e.g. "TDD.pdf_12".
    ids = [f"{c['source']}_{c['chunk_index']}" for c in chunks]
    metadatas = [{"source": c["source"], "chunk_index": c["chunk_index"]} for c in chunks]

    print(f"Embedding {len(texts)} chunks with {MODEL_NAME} ...")
    embeddings = _embed(texts)

    print("Adding to ChromaDB ...")
    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    print(f"Indexed {collection.count()} chunks into '{COLLECTION_NAME}'.")
    return collection.count()


# ---------------------------------------------------------------------------
# Stage 4: Retrieval
# ---------------------------------------------------------------------------

def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Embed `query` and return the `top_k` most similar chunks.

    Each result: {"source", "chunk_index", "text", "score"} where score is
    cosine similarity (1.0 = identical direction, higher = more relevant).
    """
    client = _get_client()
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = _embed([query])
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for text, meta, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append({
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "text": text,
            "score": 1 - distance,   # cosine distance -> cosine similarity
        })
    return hits


# ---------------------------------------------------------------------------
# Run directly: build the index, then test retrieval on the eval questions.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    build_index()

    test_questions = [
        "What does the 'S' in SOLID stand for, and what does it mean?",
        "What are the four quadrants of Martin Fowler's Technical Debt Quadrant?",
        "What are the three steps of the Test-Driven Development cycle?",
        "What is the structure of a Conventional Commit message?",
        "What standard should a reviewer use when deciding to approve a code change?",
    ]

    for q in test_questions:
        print("\n" + "=" * 80)
        print("Q:", q)
        for i, hit in enumerate(retrieve(q), 1):
            preview = hit["text"].replace("\n", " ")[:90]
            print(f"  {i}. [{hit['score']:.3f}] {hit['source']:38s} {preview}...")
