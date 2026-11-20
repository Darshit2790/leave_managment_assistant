# AI HR Assistant — Task 1: Document Intelligence (Policy RAG Service)

Ask natural-language questions about company HR policies. The assistant retrieves the most relevant
passages from your policy PDFs and answers with **source file + page number citations**. If the
policy documents don't contain the answer, it says so instead of guessing.

## How it works

```
PDFs ──► pypdf (text per page) ──► chunking (1000 chars, 150 overlap)
     ──► fastembed (local BGE embeddings) ──► ChromaDB (persistent vector store)

Question ──► embed ──► top-K similar chunks ──► similarity threshold guard
         ──► Qwen3-8B (IIT KGP API, HTTPS + CA cert) ──► answer + [file, p.N] citations
```

Design notes
- **Embeddings are local** (fastembed) because the Qwen API has no embeddings endpoint.
- **"Not available" handling** is two-layered: (1) if no chunk passes `MIN_SIMILARITY`, the LLM is
  not called at all; (2) the prompt forces the model to answer `NOT_FOUND` if context is insufficient.
- **API limits respected**: 1 request at a time, `max_tokens` ≤ 1024, short chat history (8192-token window),
  retry with 2s/4s/8s backoff on 429/503, HTTPS verification always on.
- Qwen3 "thinking" output is disabled/stripped.

## Folder structure

```
hr-assistant/
├── main.py                    # CLI entry point
├── requirements.txt           # ALL dependencies in one place
├── .env.example               # config template (copy to .env)
├── .gitignore
├── README.md
├── app/
│   ├── config.py              # settings from .env
│   ├── ingestion.py           # PDF extraction + chunking
│   ├── embeddings.py          # local embedding model
│   ├── vector_store.py        # ChromaDB wrapper
│   ├── llm_client.py          # Qwen3-8B client (cert, retries)
│   ├── api.py                 # REST API (FastAPI) = the Policy RAG service
│   └── rag.py                 # retrieval + answer + citations
├── scripts/
│   └── generate_sample_policies.py   # creates fictional sample PDFs
├── tests/
│   ├── test_chunking.py
│   └── test_api.py
├── certs/                     # put vm06-ca.crt here (git-ignored)
└── data/
    ├── policies/              # drop your HR policy PDFs here
    └── vectorstore/           # auto-generated (git-ignored)
```

## Setup (Windows PowerShell)

Requires Python 3.10+ and internet access on first run (to download the ~130 MB embedding model).

```powershell
cd "C:\Users\Ashutosh Shinde\Desktop\AI Project\hr-assistant"

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
copy "C:\Users\Ashutosh Shinde\Desktop\AI Project\vm06-ca.crt" certs\vm06-ca.crt
```

Edit `.env` and set `LLM_API_KEY=<your group key>`. Group 016–030 settings
(`https://103.42.50.41:1032/v1`, `vm06-ca.crt`) are already the defaults.
Alternatively, skip copying the cert and set
`LLM_CA_CERT=C:/Users/Ashutosh Shinde/Desktop/AI Project/vm06-ca.crt`.

> If PowerShell blocks activation: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

macOS/Linux: `source .venv/bin/activate` and `cp` instead of `copy`.

## Run

```powershell
python main.py check-llm                      # verify key + certificate work
python scripts/generate_sample_policies.py    # (optional) fictional sample PDFs
python main.py ingest                         # index everything in data/policies/
python main.py ask "How many annual leaves can I take?"
python main.py chat                           # interactive
python main.py reset                          # clear the vector DB
```

Use your own PDFs by placing them in `data/policies/` and re-running `python main.py ingest`.

Sample questions to try
- How many annual leaves can I take? → answered with citation
- Explain maternity leave eligibility → answered with citation
- How many days can I carry forward? → answered with citation
- What is the company's stock option policy? → "couldn't find in policy documents"

## Policy RAG service (REST API)

```powershell
python main.py serve            # http://127.0.0.1:8001  (Swagger UI at /docs)
```

| Method & path | Purpose |
|---|---|
| `GET /health` | Service status + number of indexed chunks |
| `GET /policies` | Indexed documents with chunk counts |
| `POST /policies/ingest` | (Re)index all PDFs in `data/policies/` |
| `POST /policies/upload` | Upload a PDF (multipart) and index it |
| `POST /policies/query` | Ask a question → answer + citations |

Query example:
```powershell
curl.exe -X POST http://127.0.0.1:8001/policies/query -H "Content-Type: application/json" `
  -d '{\"question\": \"How many annual leaves can I take?\"}'
```
Response:
```json
{
  "answer": "You are entitled to 18 days of annual leave per year [leave_policy.pdf, p.1].",
  "found": true,
  "sources": [{"source": "leave_policy.pdf", "page": 1, "score": 0.78}]
}
```
`found: false` means the policy documents don't cover the question. The Agent orchestrator (Task 2)
should call `POST /policies/query` for policy questions. Optional `history` (list of
`{question, answer}`) supports follow-ups.

## Configuration (.env)

| Variable | Default | Purpose |
|---|---|---|
| `LLM_BASE_URL` | `https://103.42.50.41:1032/v1` | Your group's API URL |
| `LLM_API_KEY` | – | Your group key (secret) |
| `LLM_CA_CERT` | `certs/vm06-ca.crt` | Path to CA certificate |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 1000 / 150 | Chunking (characters) |
| `TOP_K` | 4 | Chunks passed to the LLM |
| `MIN_SIMILARITY` | 0.45 | Below this → "not found". Raise if it answers off-topic questions; lower if it refuses valid ones |

## Tests

```powershell
pytest -q
```

## Push to GitHub

1. Create an **empty** repo on GitHub (no README/license), e.g. `hr-assistant`.
2. From the project folder:

```powershell
git init
git add .
git status          # confirm .env and *.crt are NOT listed
git commit -m "Task 1: HR policy RAG assistant"
git branch -M main
git remote add origin https://github.com/<your-username>/hr-assistant.git
git push -u origin main
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `LLM_API_KEY is not set` | Create `.env` from `.env.example` and add your key |
| `CA certificate not found` | Fix `LLM_CA_CERT` path (exact file path) |
| TLS/certificate error | Make sure you use the cert matching your URL (vm06 ↔ port 1032). Don't disable verification |
| `401` | Wrong key or URL for your group |
| `429` | Only 1 active request per key; wait (client auto-retries) |
| `503` | VM busy; client retries 3 times then reports |
| Answers "not found" for valid questions | Lower `MIN_SIMILARITY` (e.g. 0.35), confirm `ingest` ran |

## Security

Never commit `.env` or certificates (already in `.gitignore`). If your API key was shared in a chat or
screenshot, treat it as exposed and ask your coordinator for a replacement.

## Roadmap (next tasks)

2. Agent orchestrator, 3. Employee API service, 4. Leave Management API service, 5. Chat UI, 6. Integration & testing.
