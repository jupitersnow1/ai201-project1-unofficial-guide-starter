# Evaluation Notes (raw material for the README Evaluation Report + Failure Case Analysis)

> Captured during Milestone 4 retrieval testing (before generation was wired up).
> These are the *retrieval* results — which chunks came back for each question.
> Re-run with the full system in Milestone 5 to record the generated answers too.

## Retrieval results (top-k = 4, cosine similarity)

| # | Question | Top source(s) | Retrieval quality |
|---|----------|---------------|-------------------|
| 1 | What does the "S" in SOLID stand for? | digitalocean-solid (×3) | Right source, but #1 chunk was the byline/intro, not the crisp SRP definition |
| 2 | Four quadrants of Fowler's Technical Debt Quadrant? | fowler-technical-debt (×4) | Excellent — top chunk states "deliberate and inadvertent debt" |
| 3 | Three steps of the TDD cycle? | TDD.pdf (×3) + google-code-review (×1) | Good — TDD.pdf p9 retrieved; one off-topic Google hit |
| 4 | Structure of a Conventional Commit message? | conventional-commits (×2) + missing-semester-version-control (×2) | Good top hit; git-history chunks were noise |
| 5 | What standard should a reviewer use to approve a change? | google-code-review (×4) | Source right, but chunks were about escalation/ownership — NOT the "improves overall code health" standard |

Similarity scores ranged ~0.25–0.57 — low absolute values are normal for
all-MiniLM-L6-v2 when matching question-phrased queries against statement-phrased
documents; ranking still worked.

## Q5 — Before / After (the evaluation process caught a false read)

> Keeping both the initial hypothesis and the confirmed result on purpose: the
> story of testing the hypothesis is itself worth reporting, and it shows why we
> confirm a suspected failure against the full system before writing it up.

### BEFORE — initial failure hypothesis (Milestone 4, retrieval-only)

**Question:** "What standard should a reviewer use when deciding to approve a code change?"

**What retrieval returned:** four chunks from google-code-review.txt, but they
covered escalation, code ownership, and accepting author preferences — NOT the
key sentence (the reviewer should approve once the change "improves the overall
code health of the system, even if it isn't perfect").

**Suspected root cause (to confirm in M5):** the "overall code health" passage
exists in the corpus (it's on the Google standard.html page we scraped), but it
appears to have lost the top-4 ranking to other code-review chunks. Likely a
retrieval/embedding issue — the query wording ("standard… to approve") may embed
closer to the procedural chunks than to the chunk that actually states the standard.
Possible contributing factor: the answer may straddle a chunk boundary, or the
phrase "code health" isn't lexically close to "standard to approve."

**To verify in Milrstone 5:** check whether the "code health" chunk is in the index at all,
where it ranks for this query, and whether the generated answer is wrong because
of this miss. If so, this is the documented Failure Case (tied to the retrieval stage).

**Possible fixes to mention:** rephrase/expand the query, increase top-k, or
re-chunk the standard.html section so the standard statement stays intact.

### AFTER — confirmed with the full system (Milestone 5)

The hypothesis was **wrong** — Q5 actually succeeds. Running the full pipeline
(retrieval + Groq generation, temperature 0) produced a correct answer:
"A reviewer should favor approving a CL once it definitely improves the overall
code health of the system, even if the CL isn't perfect — continuous improvement
over perfection." Cited google-code-review.txt.

**Why the initial read was off:** during Milestone 4 I judged the chunks from a
90-character preview, which showed escalation/ownership text. The "improves
overall code health" standard was *inside* one of the four retrieved chunks, just
past the 90-char cutoff. Retrieval had actually surfaced the right content; the
preview hid it. So this is NOT a failure — it's a lesson that previews can
mislead, and that a suspected failure must be confirmed end-to-end.

**Consequence:** all 5 designed eval questions answer correctly, so the README
Failure Case Analysis needs a *different, genuine* failure (documented next).

## GENUINE failure case (for README Failure Case Analysis) — design patterns

**Question that failed:** "What problem does the Observer pattern solve?"

**What the system returned:** "The Observer pattern solves the *aliasing problem*,
where an object relies on the state of a shared object, but the shared object is
changed by another object without notifying the relying object." — This is
incorrect. The real Observer pattern defines a one-to-many dependency so that when
one object changes state, all its dependents are notified automatically. The answer
conflated it with a passage about "aliasing" from TDD.pdf (Kent Beck). (Related:
"How does the Singleton pattern work?" and "Explain the Factory Method pattern"
returned only thin one-line definitions.)

**Root cause (two pipeline stages):**
1. *Ingestion.* `sourcemaking-design-patterns.txt` contains only the SourceMaking
   **catalog/index page** — one-line blurbs per pattern, not the detailed pattern
   pages. So the corpus has almost no substantive Observer content. (Same table-of-
   contents scraping problem fixed for Google and refactoring.guru, but not for
   SourceMaking.)
2. *Retrieval + generation.* With no real Observer content to match, retrieval
   pulled a tangentially related TDD.pdf chunk that happened to mention "aliasing,"
   and the model produced a confident but wrong answer instead of refusing.

**What I would change to fix it:**
- Scrape the individual SourceMaking pattern sub-pages (or swap in refactoring.guru's
  design-pattern pages) so each pattern has real content — the same multi-page fix
  used for Google/refactoring.guru in scrape.py.
- Add a relevance threshold so low-similarity, off-topic chunks (a TDD chunk for a
  design-patterns question) are filtered out before generation, making the system
  more likely to say "I don't know" than to confabulate.

### FIX APPLIED — verified

Implemented fix #1: updated scrape.py so the SourceMaking source fetches the
catalog PLUS individual pattern pages (singleton, factory_method, abstract_factory,
builder, adapter, decorator, facade, observer, strategy, command). The source grew
from ~6,027 to ~47,911 chars (11 pages); the corpus grew from 205 to 246 chunks.
After rebuilding the index, re-running the questions:
- Observer: now answers from sourcemaking-design-patterns.txt (no TDD/aliasing
  conflation) — drawn from the page's actual problem description.
- Singleton: detailed correct answer, including the three criteria for when to use it.
- Factory Method: correct (virtual constructor, polymorphic creation, decoupling).

Fix #2 (relevance threshold) not yet applied — noted as a further improvement.
