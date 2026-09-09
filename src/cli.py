#!/usr/bin/env python
"""CLI entry point: scan a folder of life-admin documents and print tasks."""
import argparse
import sys
from datetime import date
from pathlib import Path

from src.main import Pipeline
from src.extraction.gateway_llm import build_gateway_llm
from src.task_engine.rules import RuleEngine
from src.task_engine.scheduler import TaskScheduler


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="life-admin",
        description="Turn receipts, subscriptions, and warranties into tasks",
    )
    parser.add_argument(
        "path", nargs="?", default="data/samples",
        help="File or folder of documents to scan (default: data/samples)",
    )
    parser.add_argument(
        "--ask", metavar="QUESTION",
        help="Ask a question against ingested documents (RAG) instead of scanning",
    )
    args = parser.parse_args(argv)

    target = Path(args.path)
    if not target.exists():
        print(f"Path not found: {target}", file=sys.stderr)
        return 1

    if args.ask:
        from src.rag.service import RagService

        rag = RagService(samples_dir=str(target))
        rag.ingest()
        results = rag.query(args.ask, top_k=5)
        if not results:
            print(f"No documents matched {args.ask!r}")
            return 0
        print(f"Top matches for {args.ask!r}:")
        for r in results:
            c = r["chunk"]
            print(f"\n[{r['citation']}] (score {r['score']})")
            print(f"  {c['text'][:200]}")
        return 0

    files = (
        [str(target)] if target.is_file()
        else [str(p) for p in sorted(target.iterdir()) if p.suffix.lower() in (".pdf", ".txt", ".md", ".eml")]
    )
    if not files:
        print(f"No documents (.pdf/.txt/.md/.eml) found in {target}", file=sys.stderr)
        return 1

    pipeline = Pipeline(
        rules=RuleEngine(today=date.today()),
        scheduler=TaskScheduler(today=date.today()),
        llm=build_gateway_llm(),  # None when no gateway configured
    )
    result = pipeline.run(files)

    print(result["formatted"])
    print(f"\n{result['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
