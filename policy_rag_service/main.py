"""CLI entry point.

  python main.py check-llm          # test API key + certificate
  python main.py ingest             # index PDFs in data/policies/
  python main.py ask "How many annual leaves can I take?"
  python main.py chat               # interactive chat
  python main.py serve              # start REST API on http://localhost:8001
  python main.py reset              # wipe the vector DB
"""
import argparse
import sys

from app.config import settings

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def cmd_ingest(_):
    from app.ingestion import load_pdf
    from app.vector_store import PolicyVectorStore

    pdfs = sorted(settings.policies_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {settings.policies_dir}.\n"
              "Add your policy PDFs there, or run: python scripts/generate_sample_policies.py")
        return 1
    store = PolicyVectorStore()
    for pdf in pdfs:
        chunks = load_pdf(pdf, settings.chunk_size, settings.chunk_overlap)
        store.add_chunks(chunks)
        print(f"Indexed {pdf.name}: {len(chunks)} chunks")
    print(f"Done. Total chunks in vector DB: {store.count()}")
    return 0


def _print_result(res):
    print(f"\nAssistant: {res.answer}")
    if res.sources:
        print("\nSources:")
        for s in res.sources:
            print(f"  - {s['source']} (page {s['page']}, similarity {s['score']})")


def cmd_ask(args):
    from app.rag import PolicyRAG

    _print_result(PolicyRAG().answer(args.question))
    return 0


def cmd_chat(_):
    from app.rag import PolicyRAG

    rag = PolicyRAG()
    history = []
    print("HR Policy Assistant (type 'exit' to quit)\n")
    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"exit", "quit"}:
            break
        if not q:
            continue
        res = rag.answer(q, history)
        _print_result(res)
        history.append((q, res.answer))
        print()
    return 0


def cmd_check(_):
    from app.llm_client import LLMClient

    print("LLM replied:", LLMClient().ping())
    return 0


def cmd_serve(args):
    import uvicorn

    uvicorn.run("app.api:app", host=args.host, port=args.port)
    return 0


def cmd_reset(_):
    from app.vector_store import PolicyVectorStore

    PolicyVectorStore().reset()
    print("Vector DB cleared.")
    return 0


def main():
    p = argparse.ArgumentParser(description="AI HR Assistant - Policy RAG")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-llm").set_defaults(fn=cmd_check)
    sub.add_parser("ingest").set_defaults(fn=cmd_ingest)
    sub.add_parser("chat").set_defaults(fn=cmd_chat)
    sub.add_parser("reset").set_defaults(fn=cmd_reset)
    sv = sub.add_parser("serve")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8001)
    sv.set_defaults(fn=cmd_serve)
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.set_defaults(fn=cmd_ask)
    args = p.parse_args()
    try:
        sys.exit(args.fn(args))
    except Exception as e:  # friendly errors for LLMError etc.
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
