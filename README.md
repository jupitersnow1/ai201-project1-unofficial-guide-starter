# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## How to Run

### 1. Setup (one time)
```bash
python -m venv .venv && source .venv/bin/activate   # create + activate the environment
pip install -r requirements.txt                     # install dependencies
cp .env.example .env                                 # then put your Groq API key in .env
```
Get a free Groq API key at https://console.groq.com and set `GROQ_API_KEY` in `.env`.

### 2. Collect documents and build the index
```bash
python scrape.py          # download the web sources into documents/ (optional; the repo already includes them)
python vector_store.py    # embed all chunks into a local ChromaDB index (run once)
```

### 3. Ask questions — three ways
```bash
python generate.py            # launch the web interface (opens at http://127.0.0.1:7860)
python generate.py --cli      # interactive terminal: type questions at the prompt
python generate.py --ask "What are the three steps of the TDD cycle?"   # one-shot
python generate.py --test     # run a built-in demo set (5 eval questions + a grounding refusal)
```

### Using the web interface
1. Open the printed URL (`http://127.0.0.1:7860`) in a browser.
2. Type a question (e.g. *"When should you use the Singleton pattern?"*) and click **Ask** (or press Enter).
3. The answer appears with a `Sources:` line naming the file(s) it used.
4. Expand **"Retrieved chunks (the grounding)"** to see the four chunks the answer was built from, each with its source file and similarity score.

Try an off-topic question (e.g. *"What's the best topping for a pizza?"*) to see grounding in action — the system replies *"I don't know based on the provided sources."* rather than answering from outside knowledge.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

This system covers **software development best practices** — software design, testing strategies, code review, refactoring, technical debt, version control, and commit conventions. This knowledge helps students and early-career developers evaluate design alternatives, catch problems early, and build maintainable, testable software rather than just code that runs.

It is valuable because, while material on software development exists, practical guidance on *design and engineering practice* is scattered across engineering blogs, official documentation, course notes, specifications, and discussion forums. Many CS students spend significant time on data-structures-and-algorithms interview prep but have far fewer opportunities to learn the production-quality engineering practices used on real teams. This RAG system pulls that scattered knowledge into one searchable place.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | DigitalOcean — SOLID Principles | Article | [link](https://www.digitalocean.com/community/conceptual-articles/s-o-l-i-d-the-first-five-principles-of-object-oriented-design) → `documents/digitalocean-solid.txt` |
| 2 | SourceMaking — Design Patterns | Article | [link](https://sourcemaking.com/design_patterns) → `documents/sourcemaking-design-patterns.txt` |
| 3 | Google Engineering Practices — Code Review | Documentation | [link](https://google.github.io/eng-practices/review/) → `documents/google-code-review.txt` |
| 4 | Kent Beck — Test-Driven Development (trimmed to 31 pp.) | Book (PDF) | `documents/TDD.pdf` |
| 5 | Martin Fowler — Technical Debt Quadrant | Blog post | [link](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html) → `documents/fowler-technical-debt.txt` |
| 6 | Refactoring Guru — Code Smells | Article | [link](https://refactoring.guru/refactoring/smells) → `documents/refactoring-guru-code-smells.txt` |
| 7 | MIT Missing Semester — Version Control (Git) | Course notes | [link](https://missing.csail.mit.edu/2020/version-control/) → `documents/missing-semester-version-control.txt` |
| 8 | MIT Missing Semester — Debugging & Profiling | Course notes | [link](https://missing.csail.mit.edu/2020/debugging-profiling/) → `documents/missing-semester-debugging.txt` |
| 9 | Software Engineering Stack Exchange — "Is unit testing / TDD worthwhile?" | Forum discussion | [link](https://softwareengineering.stackexchange.com/questions/140156/is-unit-testing-or-test-driven-development-worthwhile) → `documents/stackexchange-tdd-worthwhile.txt` |
| 10 | Conventional Commits 1.0.0 | Specification | [link](https://www.conventionalcommits.org/en/v1.0.0/) → `documents/conventional-commits.txt` |

Sources were collected with `scrape.py` (web pages → main-article text via trafilatura; the Kent Beck book was added as a trimmed PDF). They span varied subtopics (design, patterns, code review, testing, technical debt, refactoring, version control, debugging, commit conventions) and varied perspectives — official docs and specifications alongside a community forum thread that argues the *skeptical* side of TDD.

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** 256 tokens (measured with the embedding model's own tokenizer).

**Overlap:** 50 tokens (~20% of each chunk).

**Why these choices fit your documents:**
The corpus is mostly conceptual articles, documentation, and course notes. I set the chunk size to 256 tokens to **match the maximum sequence length of `all-MiniLM-L6-v2`** — the model truncates anything longer than 256 tokens, so a larger chunk would be partly ignored at embedding time. 256 is therefore the largest size that is embedded in full while still being narrow enough to isolate a single concept (e.g. one SOLID principle, one code smell, one technical-debt quadrant) for precise retrieval. The 50-token overlap (~20%) keeps a concept that straddles a chunk boundary from being lost — without it, an explanation could be split so that neither chunk holds the whole idea.

**Preprocessing before chunking:**
- **PDF:** read with `pdfplumber`, using `page.dedupe_chars()` to remove the doubled characters that bold text produces (e.g. "Dollar" → "DDoollllaarr").
- **Web pages:** fetched with `trafilatura`, which extracts main-article text and strips nav bars, ads, footers, and cookie banners.
- **All text:** collapsed redundant whitespace/blank lines.
- **Chunking:** done by the tokenizer's **offset mapping** — tokens are used only to find cut points, and the chunk text is sliced from the *original* string so capitalization and punctuation are preserved (important for readable source citations).

**Final chunk count:** 246 chunks across 10 documents.

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** `all-MiniLM-L6-v2`, loaded through `sentence-transformers` (384-dimension embeddings). I chose it because it runs locally with no API key or cost, is fast, and works well for general-purpose semantic search. Its 256-token limit is also what the chunking strategy is built around, so the model and the chunks are aligned. Embeddings are stored in a persistent **ChromaDB** collection (cosine similarity), and retrieval returns the **top 4** chunks per query.

**Production tradeoff reflection:**
If I deployed this for real users and cost were not a concern, I would consider a higher-capacity embedding model. `all-MiniLM-L6-v2` is fast and free but small, and its 256-token cap forces small chunks. A model with a longer context window (e.g. `BAAI/bge-base-en-v1.5` at 512 tokens, or a hosted API model like OpenAI's `text-embedding-3-large`) would allow larger chunks that capture a whole concept and would generally be more accurate on domain-specific technical text. The tradeoffs I would weigh: **context length** (longer = fewer truncation problems), **accuracy on technical text**, **latency** (a hosted API adds network round-trips a local model avoids), and **cost and privacy** (API models charge per token and send data off-machine, while the local model is free and keeps everything in-house). For this project the local model is the right call; at production scale I would likely trade some speed and cost for accuracy and longer context.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
Generation uses a Groq-hosted LLM (`llama-3.3-70b-versatile`) at temperature 0, with this system prompt:

> You are an assistant that answers questions about software development best practices.
> Follow these rules strictly:
> - Answer using ONLY the information in the CONTEXT provided in the user's message.
> - If the context does not contain enough information to answer the question, reply with exactly: "I don't know based on the provided sources."
> - Do NOT use any outside or prior knowledge, and do not guess or invent details.
> - Keep the answer concise and accurate.
> - End your answer with a "Sources:" line listing the source file name(s) you actually used.

Structurally, the retrieved chunks are passed in the *user* message as a labeled `CONTEXT:` block (each chunk prefixed with `[Source: <filename>]`), followed by the question. Temperature 0 keeps answers deterministic and factual. I verified grounding works by asking an off-topic question ("What is the best topping for a pizza?"): even though retrieval still returned four software chunks, the model correctly replied "I don't know based on the provided sources" instead of answering from prior knowledge.

**How source attribution is surfaced in the response:**
Two ways. (1) The model ends each answer with a `Sources:` line naming the file(s) it actually used (e.g. `fowler-technical-debt.txt`). (2) The Gradio interface shows the retrieved chunks in an expandable "Retrieved chunks (the grounding)" panel, each labeled with its source file and cosine-similarity score, so a user can see exactly which passages the answer was built from.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What does the "S" in SOLID stand for? | Single Responsibility Principle — a class should have only one reason to change | "Single-Responsibility Principle (SRP)… a class should have one and only one reason to change." Cited digitalocean-solid.txt | Relevant (1 stray conventional-commits chunk, unused) | Accurate |
| 2 | Four quadrants of Fowler's Technical Debt Quadrant? | Reckless/Prudent × Deliberate/Inadvertent | Listed all four (Prudent/Reckless × Deliberate/Inadvertent), even noting Fowler questions the prudent-inadvertent one. Cited fowler-technical-debt.txt | Relevant (4/4 from correct source) | Accurate |
| 3 | Three steps of the TDD cycle? | Red, Green, Refactor | "Red — write a failing test; Green — make it pass quickly; Refactor — remove duplication." Cited TDD.pdf | Relevant (3/4 TDD; 1 stray Google chunk, unused) | Accurate |
| 4 | Structure of a Conventional Commit message? | `<type>[scope]: <description>` + optional body/footer | "`<type>[optional scope]: <description>` / body / footer(s)." Cited conventional-commits.txt | Relevant (top hit correct; 2 git-history chunks, unused) | Accurate |
| 5 | What standard should a reviewer use to approve a change? | Approve once it improves overall code health, even if imperfect | "Approve once the CL definitely improves the overall code health of the system, even if it isn't perfect." Cited google-code-review.txt | Relevant (4/4 from correct source) | Accurate |

**Retrieval quality:** Relevant — the correct source ranked in the top 4 for all five questions. Minor cross-source noise appeared (e.g. a conventional-commits chunk for the SOLID query), but the generation step consistently used and cited only the relevant source.
**Response accuracy:** Accurate — all five designed questions were answered correctly. (Note: this is the *designed* question set; a separate probing question about design patterns exposed a real failure, analyzed below.)

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** "What problem does the Observer pattern solve?" (a probing question outside the 5 designed ones)

**What the system returned:** "The Observer pattern solves the *aliasing problem*, where an object relies on the state of a shared object, but the shared object is changed by another object without notifying the relying object." This is incorrect — the Observer pattern actually defines a one-to-many dependency so that when one object changes state, all dependents are notified automatically. The model conflated it with a passage about "aliasing" pulled from TDD.pdf. (Related: questions about the Singleton and Factory Method patterns returned only thin one-line definitions.)

**Root cause (tied to specific pipeline stages):** This is primarily an **ingestion** failure with a **retrieval/generation** consequence. `documents/sourcemaking-design-patterns.txt` was scraped from only the SourceMaking *catalog/index* page, which contains one-line blurbs per pattern rather than the detailed pattern pages — so the corpus has almost no substantive Observer content. (This is the same table-of-contents scraping problem I caught and fixed for the Google and refactoring.guru sources, but did not fix for SourceMaking.) With no real Observer content to match, retrieval pulled a tangentially related TDD.pdf chunk that happened to contain the word "aliasing," and the LLM produced a confident but wrong answer instead of refusing.

**What I would change to fix it — and the fix I applied:** I updated `scrape.py` to fetch the individual SourceMaking pattern sub-pages (singleton, factory method, observer, strategy, etc.) in addition to the catalog — the same multi-page approach already used for the Google and refactoring.guru sources. This grew that source from ~6K to ~48K characters and the corpus from 205 to 246 chunks. After rebuilding the index, the same question now returns a correct, source-grounded answer for the Observer pattern (and detailed answers for Singleton and Factory Method), with no more conflation from TDD.pdf. A further improvement I have *not* yet made would be to add a relevance threshold so low-similarity, off-topic chunks are filtered out before generation — that would make the system fall back to "I don't know based on the provided sources" rather than confabulate when a topic genuinely isn't covered.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
Writing the Chunking Strategy section ahead of time forced me to make concrete decisions about chunk size, overlap, and the limitations of the all-MiniLM-L6-v2 embedding model. Because I had already established that chunks should remain within the model's 256-token limit, I quickly recognized that my initial chunking approach was producing oversized chunks and corrected it before moving on to embeddings. The evaluation questions were also helpful because they gave me a clear way to test retrieval as soon as the index was built, rather than relying on ad hoc queries and assumptions about whether the system was working.

**One way your implementation diverged from the spec, and why:**
Several source decisions changed once I began collecting and processing documents. I replaced the full Martin Fowler Refactoring PDF with Refactoring.Guru's code-smells content because the book was significantly larger than the rest of the corpus and was dominating retrieval results. I also changed one source to a Stack Exchange discussion about the value of TDD, trimmed the Kent Beck TDD PDF to focus on the most relevant conceptual sections, and added a scrape.py script to help collect and organize source material.

I ended up making these changes after working with the documents directly and seeing how they behaved in the pipeline. Some sources were too large, some PDFs introduced extraction issues, and others were not as helpful for retrieval as I expected. Updating the corpus helped keep the content balanced and improved the overall quality of the knowledge base.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1 — token-accurate chunking**

- *What I gave the AI:* My Chunking Strategy section from planning.md (256-token chunks, 50-token overlap, all-MiniLM-L6-v2) and asked it to help implement load_documents() and chunk_text().

- *What it produced:* An initial version of ingest.py that loaded documents and created chunks by decoding token IDs back into text. While the overall approach worked, testing on real documents revealed issues with formatting, capitalization, and chunk length that I later corrected.


- *What I changed or overrode:* After testing on my actual documents, I noticed that some chunks were losing capitalization and punctuation, and a few even exceeded the model's 256-token limit. This happened because the original implementation reconstructed chunks from token IDs, which did not preserve the original text formatting. To fix this, I changed the chunking logic to use the tokenizer only for determining chunk boundaries and then slice directly from the original text. This preserved the formatting of the source documents and ensured that all chunks stayed within the model's token limit. I only discovered this issue by testing on real project data, since it did not appear in the initial synthetic tests.

**Instance 2 — fixing garbled PDF extraction**

- *What I gave the AI:* The requirement to read PDFs (the Kent Beck TDD book) with pdfplumber.
- *What it produced:* A reader using plain `page.extract_text()`.
- *What I changed or overrode:* During the chunk-inspection step I saw the bold code samples were doubled ("Dollar" -> "DDoollllaarr") because PDFs render bold by overprinting glyphs. I changed the reader to `page.dedupe_chars().extract_text()`, which removed all the doubling (verified: 0 doubled-bold artifacts across the corpus). This was the "noisy PDF extraction" risk I had predicted in planning.md, caught and fixed before embedding.
