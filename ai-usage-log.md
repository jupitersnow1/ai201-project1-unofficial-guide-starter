# AI Usage Log

> Running notes for the README "AI Usage" section. Each time I use an AI tool to produce pipeline code, I record: what I gave it, what it produced, and **what I changed or overrode**. The override is the part that matters for grading.

## Milestone 3 — Ingestion and chunking
- _What I gave the AI:_ 

I shared my Chunking Strategy from `planning.md` (256-token chunks with a 50-token overlap using `all-MiniLM-L6-v2`) and asked for assistance implementing two functions: `load_documents()`, which loads PDFs, text files, markdown files, and HTML files, and `chunk_text()`, which splits documents according to the chunking strategy I selected.


- _What it produced:_ 

I implemented an `ingest.py` module that loads documents from multiple file formats, performs light text cleaning, and splits documents into overlapping token-based chunks using a sliding-window approach. The module also includes a `__main__` block that prints chunk statistics, making it easier to verify that documents are being ingested and chunked correctly.

- _What I changed or overrode:_ 

The initial implementation created chunks by decoding token IDs back into text. When I tested it on my real documents (the SOLID Principles article and TDD PDF), I noticed the chunks were losing capitalization, punctuation looked awkward, and some chunks exceeded the 256-token limit. Since all-MiniLM-L6-v2 is an uncased model, reconstructing text from tokens was altering the original content. To fix this, I changed the chunker to use the tokenizer's offset mapping. The tokenizer is now used only to determine chunk boundaries, while the chunks themselves are sliced directly from the original text. This preserved formatting and kept chunks within the model's token limit.

A second issue appeared during the required chunk inspection. The TDD PDF contained bold code examples where every character was duplicated (for example, "Dollar" became "DDoollllaarr"). This happened because PDFs often render bold text by drawing characters multiple times. The original implementation used extract_text(), which captured those duplicate glyphs. I updated the PDF reader to use page.dedupe_chars().extract_text(), which removed the duplicated characters before extraction. After re-running ingestion, the duplicated text was eliminated across all extracted chunks.

Both issues were only discovered by testing on real source documents and inspecting the generated chunks. They did not appear in the initial synthetic tests, reinforcing the importance of validating the pipeline with actual project data before generating embeddings.

## Milestone 4 — Embedding and retrieval
- _What I gave the AI:_
- _What it produced:_
- _What I changed or overrode:_

## Milestone 5 — Generation and interface
- _What I gave the AI:_
- _What it produced:_
- _What I changed or overrode:_
