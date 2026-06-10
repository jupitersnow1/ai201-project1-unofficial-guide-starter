"""
Source collector for Milestone 3.

Instead of copy-pasting every source by hand, this script downloads the ones
that can be fetched cleanly and writes them into documents/ in the format
ingest.py expects:

  - HTML articles  -> fetched and reduced to main-article text with trafilatura
                      (this strips nav bars, ads, footers, cookie banners), saved as .txt
  - PDFs           -> downloaded as-is and saved as .pdf (ingest.py reads them)

Some sources are intentionally NOT scraped and must be added by hand:
  - The Refactoring book: too long; save only the "Bad Smells in Code" chapter
    so one source doesn't dominate retrieval.

Run:  python scrape.py
Then ALWAYS re-run ingest.py and inspect the chunks — scraping does not remove
the inspection step.
"""

import sys
from pathlib import Path

import requests
import trafilatura

DOCUMENTS_DIR = Path(__file__).parent / "documents"

# Pretend to be a normal browser; some sites reject the default requests UA.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Each source: the output filename, its URL, and how to fetch it.
#   method "html" -> extract article text, save .txt
#   method "pdf"  -> download bytes, save .pdf
SOURCES = [
    {"name": "digitalocean-solid",          "method": "html", "url": "https://www.digitalocean.com/community/conceptual-articles/s-o-l-i-d-the-first-five-principles-of-object-oriented-design"},
    # The /design_patterns landing page is only a catalog of one-line blurbs, so
    # we fetch the catalog plus individual pattern pages (spanning creational,
    # structural, and behavioral patterns) for real content.
    {"name": "sourcemaking-design-patterns","method": "html", "url": [
        "https://sourcemaking.com/design_patterns",
        "https://sourcemaking.com/design_patterns/singleton",
        "https://sourcemaking.com/design_patterns/factory_method",
        "https://sourcemaking.com/design_patterns/abstract_factory",
        "https://sourcemaking.com/design_patterns/builder",
        "https://sourcemaking.com/design_patterns/adapter",
        "https://sourcemaking.com/design_patterns/decorator",
        "https://sourcemaking.com/design_patterns/facade",
        "https://sourcemaking.com/design_patterns/observer",
        "https://sourcemaking.com/design_patterns/strategy",
        "https://sourcemaking.com/design_patterns/command",
    ]},
    # The /review/ landing page is only a table of contents, so we fetch the
    # substantive sub-pages and concatenate them into one document.
    {"name": "google-code-review",          "method": "html", "url": [
        "https://google.github.io/eng-practices/review/reviewer/standard.html",
        "https://google.github.io/eng-practices/review/reviewer/looking-for.html",
        "https://google.github.io/eng-practices/review/reviewer/comments.html",
    ]},
    {"name": "fowler-technical-debt",       "method": "html", "url": "https://martinfowler.com/bliki/TechnicalDebtQuadrant.html"},
    # Code smells: the /smells catalog page is just a list, so we fetch the
    # catalog intro plus a representative set of individual smell pages.
    {"name": "refactoring-guru-code-smells", "method": "html", "url": [
        "https://refactoring.guru/refactoring/smells",
        "https://refactoring.guru/smells/long-method",
        "https://refactoring.guru/smells/large-class",
        "https://refactoring.guru/smells/primitive-obsession",
        "https://refactoring.guru/smells/long-parameter-list",
        "https://refactoring.guru/smells/data-clumps",
        "https://refactoring.guru/smells/duplicate-code",
        "https://refactoring.guru/smells/dead-code",
        "https://refactoring.guru/smells/feature-envy",
        "https://refactoring.guru/smells/shotgun-surgery",
    ]},
    {"name": "missing-semester-version-control", "method": "html", "url": "https://missing.csail.mit.edu/2020/version-control/"},
    {"name": "missing-semester-debugging",  "method": "html", "url": "https://missing.csail.mit.edu/2020/debugging-profiling/"},
    {"name": "conventional-commits",        "method": "html", "url": "https://www.conventionalcommits.org/en/v1.0.0/"},
    # Community discussion: practitioner debate on whether TDD/unit testing is
    # worthwhile — the skeptic counterpoint to the pro-TDD Kent Beck source.
    {"name": "stackexchange-tdd-worthwhile", "method": "html", "url": "https://softwareengineering.stackexchange.com/questions/140156/is-unit-testing-or-test-driven-development-worthwhile"},
    # TDD.pdf is already in documents/. Add the Kent Beck PDF here only if you
    # want the script to (re)download it:
    # {"name": "kent-beck-tdd", "method": "pdf", "url": "https://www2.cs.uh.edu/~rsingh/documents/software_design/TDD.pdf"},
]

# Sources that need a human; printed as reminders at the end.
MANUAL_SOURCES = [
    "TDD.pdf: Has been trimmed to 31 pages and resides in documents/",
]


def fetch_html(url: str) -> str | None:
    """Download a page and return its main-article text, or None on failure."""
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        return None
    return trafilatura.extract(downloaded, include_comments=False, include_tables=True)


def fetch_pdf(url: str, dest: Path) -> bool:
    """Download a PDF to dest. Returns True on success."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return True


def main() -> None:
    DOCUMENTS_DIR.mkdir(exist_ok=True)
    results = []

    for src in SOURCES:
        name, method, url = src["name"], src["method"], src["url"]
        try:
            if method == "html":
                urls = url if isinstance(url, list) else [url]
                parts = [t for u in urls if (t := fetch_html(u))]
                text = "\n\n".join(parts)
                if not text or len(text.strip()) < 200:
                    results.append((name, "FAILED (no/too little text extracted)"))
                    continue
                dest = DOCUMENTS_DIR / f"{name}.txt"
                dest.write_text(text, encoding="utf-8")
                pages = f" ({len(parts)} pages)" if len(urls) > 1 else ""
                results.append((name, f"OK  -> {dest.name}  ({len(text):,} chars){pages}"))
            elif method == "pdf":
                dest = DOCUMENTS_DIR / f"{name}.pdf"
                fetch_pdf(url, dest)
                results.append((name, f"OK  -> {dest.name}  ({dest.stat().st_size:,} bytes)"))
        except Exception as e:  # noqa: BLE001 - report any failure per-source, keep going
            results.append((name, f"FAILED ({type(e).__name__}: {e})"))

    print("\n=== Scrape results ===")
    for name, status in results:
        print(f"  {name:38s} {status}")

    print("\n=== Add these by hand ===")
    for note in MANUAL_SOURCES:
        print(f"  - {note}")

    print("\nNext: run `python ingest.py`, then READ a few chunks from each new "
          "source to confirm the text is clean before embedding.")


if __name__ == "__main__":
    sys.exit(main())
