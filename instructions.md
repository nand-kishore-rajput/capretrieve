# CapRetrieve — Running the Project

## Prerequisites

- Podman + podman-compose installed on the server
- SSH access to `serv-7101.kl.dfki.de`
- An OpenRouter API key (get one at https://openrouter.ai)
- Optionally a Tavily API key for live web search (https://tavily.com)

---

## Step 1 — Configure environment variables (one-time)

```bash
cd ~/capretrieve
cp .env.example .env
```

Edit `.env` and fill in your keys:

```
OPENROUTER_API_KEY=sk-or-...
WEB_SEARCH_API_KEY=tvly-...     # optional — without it, web search runs in keyless/rate-limited mode
```

All other values have sensible defaults and don't need to be changed for local development.

---

## Step 2 — Build the Docker image

Only needed once, and again whenever `pyproject.toml` changes (new dependencies).

```bash
cd ~/capretrieve
podman build -t capretrieve:dev .
```

---

## Step 3 — Start the container

```bash
podman-compose up -d
```

Confirm it's running:

```bash
podman ps | grep capretrieve
# expected output:
# cee603...  localhost/capretrieve:dev  /bin/bash  Up X seconds  0.0.0.0:18000->8000/tcp  capretrieve_capretrieve_1
```

> **Note:** The container maps host port `18000` → container port `8000`. Port 8000 is already in use by another service on this server, so always use 18000 when accessing from outside the container.

---

## Step 4 — Start the API server

Exec into the running container:

```bash
podman-compose exec capretrieve bash
```

Inside the container, start uvicorn:

```bash
uvicorn capretrieve.api.main:app --host 0.0.0.0 --port 8000 --log-level debug
```

You should see:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 5 — Access from your Mac

Open a new terminal on your Mac and create an SSH tunnel:

```bash
ssh -L 18000:localhost:18000 rajput@serv-7101.kl.dfki.de
```

Keep this terminal open. Then open your browser at:

```
http://localhost:18000/docs
```

This gives you FastAPI's interactive UI where you can try all three endpoints directly.

---

## Available endpoints

| Endpoint      | Method | Purpose                                                           |
| ------------- | ------ | ----------------------------------------------------------------- |
| `/docs`       | GET    | Interactive API explorer (Swagger UI)                             |
| `/query`      | POST   | Submit a query — returns answer, evidence, and full routing trace |
| `/trace/view` | GET    | Same as `/query`, rendered as an HTML page for the browser        |
| `/connectors` | GET    | View all registered connector manifests                           |
| `/health`     | GET    | Check the status of each connector                                |

### Example query

In the `/docs` UI, expand `POST /query`, click **Try it out**, and enter:

```json
{
  "query": "What other notes link to my project retrospective, and what did those say?",
  "top_k": 5
}
```

Or open the routing trace for the same query directly in your browser:

```
http://localhost:18000/trace/view?query=What+other+notes+link+to+my+project+retrospective
```

---

## Running tests

```bash
podman-compose exec capretrieve bash
# inside the container:
pytest tests/ -v
```

Expected result: **292 passed, 2 skipped** (S2 and S3 are intentionally deferred to Phase 6).

---

## Troubleshooting

**Container name already in use / stuck overlay:**

```bash
rm -rf ~/.local/share/containers/storage/overlay/<stuck-hash>
podman rm -f capretrieve_capretrieve_1
podman-compose up -d
```

**Image not found / podman trying to pull from Docker Hub:**
Make sure `docker-compose.yml` contains `pull_policy: never`, then rebuild:

```bash
podman build -t capretrieve:dev .
podman-compose up -d
```

**`pyproject.toml` changed (new dependency added):**

```bash
podman build -t capretrieve:dev .   # rebuild the image
podman-compose down
podman-compose up -d
```

**OpenRouter returns 404 or "not a valid model ID":**
Check `ANALYZER_MODEL` and `SYNTHESIS_MODEL` in your `.env` against the current model list at https://openrouter.ai/anthropic. The default is `anthropic/claude-sonnet-5`.

**Empty answer / null content from OpenRouter:**
The model exhausted `max_tokens` on internal reasoning before producing output. The error log will say `EmptyCompletionError` with `finish_reason=length`. Raise `MAX_TOKENS` in `.env` or switch to a non-reasoning mod
