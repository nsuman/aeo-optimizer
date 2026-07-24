# AEO Optimizer (FastAPI + Google ADK)

Local backend that accepts a Shopify Admin GraphQL `products` JSON payload, runs a Google ADK orchestrator that fans out one product agent per item, and returns structured **Agentic Engine Optimization (AEO)** diffs.

## Setup

```bash
cd /home/nsuman/Documents/backend
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY
```

## Run

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open <http://localhost:8000> for the web UI: it loads the sample catalog, runs the agents, and renders per-product scores, findings, and before/after patches.

Health check: `GET http://localhost:8000/health`

## Deploy on Render

This repo includes a `Dockerfile` and `render.yaml`.

1. Push the repo to GitHub/GitLab (keep `.env` local — it is gitignored).
2. In Render: **New → Blueprint** and select this repo, **or** **New → Web Service** and point it at the repo (Docker runtime).
3. Set the secret env var **`GOOGLE_API_KEY`** in the Render dashboard (Blueprint marks it as unsynced so you enter it once).
4. Deploy. Open the service URL — same UI as local (`/`).

Notes:
- Free plan spins down after idle; the first request after sleep can take ~30–60s to wake.
- Agent runs can take 15–30s+. Free HTTP request limits can cut off large catalogs; `MAX_PRODUCTS` defaults to `10` on Render. Upgrade to **Starter** if you need always-on or longer runs.
- Do not put the API key in `render.yaml` or commit it.

Local Docker check:

```bash
docker build -t aeo-optimizer .
docker run --rm -p 8000:8000 -e GOOGLE_API_KEY=your_key aeo-optimizer
```

## Smoke test

```bash
curl -s -X POST http://localhost:8000/v1/optimize \
  -H 'Content-Type: application/json' \
  -d @samples/shopify_products.json | python -m json.tool
```

Expected shape:

```json
{
  "products": [
    {
      "product_id": "gid://shopify/Product/1001",
      "score_before": 35,
      "score_after": 72,
      "findings": [
        {
          "severity": "high",
          "code": "vague_title",
          "message": "..."
        }
      ],
      "patches": [
        {
          "path": "/title",
          "op": "replace",
          "before": "Amazing Soft Tee!!!",
          "after": "...",
          "rationale": "..."
        }
      ]
    }
  ]
}
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI |
| `GET` | `/health` | Liveness |
| `GET` | `/v1/sample` | Sample Shopify catalog used by the UI |
| `POST` | `/v1/optimize` | Run AEO agents on catalog JSON |

Request body matches Shopify GraphQL `products` connection shape (`products.nodes[...]`). A flat `products: [...]` list is also accepted. Catalogs larger than `MAX_PRODUCTS` (default 20) return `422`.

## Architecture

1. FastAPI validates and normalizes the Shopify catalog.
2. `AdkOptimizeService` seeds an in-memory ADK session with `products`.
3. `AeoOrchestratorAgent` builds one `LlmAgent` per product and runs them via `ParallelAgent`.
4. Each product agent returns an `AeoProductDiff` (scores, findings, JSON Pointer patches).
5. The orchestrator aggregates into `aeo_report`; the API returns `{ "products": [...] }`.

v1 returns diffs only — it does not write back to Shopify.

## Optional ADK web UI

```bash
adk web aeo_optimizer
```

The HTTP API (`uvicorn app.main:app`) is the primary entrypoint.