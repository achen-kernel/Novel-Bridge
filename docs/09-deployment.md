# Deployment

## Remote Root

Remote root:

```text
/home/wk/novelbridge
```

Required structure follows `STRUCTURE.md`.

## Protected Remote Paths

Do not delete:

- `deploy/remote/.env`
- `deploy/remote/ports.env`
- `models/`
- `data/`
- `training/LLaMA-Factory/`
- `runtime/`
- `logs/`

## Fixed Ports

```text
MYSQL_PORT=13306
NEO4J_HTTP_PORT=17474
NEO4J_BOLT_PORT=17687
LLAMA_PORT=18080
RAG_AGENT_PORT=18081
QDRANT_PORT=16333
```

If these change, Java config, scripts, and tunnel setup must change together.

## Deployment Artifacts

Tracked and deployable:

```text
apps/
deploy/remote/docker-compose.yml
deploy/remote/nb_up.sh
deploy/remote/nb_down.sh
deploy/remote/nb_healthcheck.sh
deploy/remote/schema.sql
scripts/
docs/
```

Not tracked:

```text
.env
data volumes
logs
runtime pid files
model files
venv/conda envs
```

## Health Check Contract

`nb_healthcheck.sh` should verify:

- MySQL accepts a query.
- Neo4j HTTP/Bolt responds with configured auth.
- llama-server returns `/v1/models`.
- rag-agent returns `/health`.
- Qdrant returns a healthy collections/service response once retrieval is enabled.
- required directories exist and are writable.

## llama-server Contract

Qwen3.5 through native `llama-server` must be started with an explicit chat template and reasoning disabled. Without this, `/v1/chat/completions` may return an empty `message.content`.

Required flags:

```bash
--chat-template-file /home/wk/novelbridge/models/Qwen3.5-9B/chat_template.jinja
--jinja
--reasoning off
```

`deploy/remote/nb_up.sh`, `deploy/remote/nb_remote.sh`, and `scripts/remote/start_llama.sh` should stay consistent on these flags.

## Agent Runtime Schema

ReaderAgent answer mode writes execution records to:

- `novel_agent_run`
- `novel_agent_step`
- `novel_retrieval_trace`

`novel_retrieval_trace` is part of the maintained schema and should not rely only on runtime auto-create in production.

## Retrieval Configuration

Default environment placeholders:

```env
QDRANT_URL=http://127.0.0.1:16333
QDRANT_COLLECTION_CHUNKS=novel_chunks
QDRANT_COLLECTION_CHAPTER_FACTS=novel_chapter_facts
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
EMBEDDING_DIM=1024
EMBEDDING_DISTANCE=cosine
EMBEDDING_DEVICE=cuda
```

`Qwen3-Embedding-0.6B` should live under the remote `models/` tree or be configured through a local model cache. Do not download models in deployment scripts unless the user explicitly asks.

## Upload Workflow

From local project root:

```bash
tar czf novelbridge.tar.gz apps/ deploy/ scripts/ docs/
scp novelbridge.tar.gz wk@<remote-server-ip>:/home/wk/novelbridge/
ssh wk@<remote-server-ip> "cd /home/wk/novelbridge && tar xzf novelbridge.tar.gz"
```

## Known Deployment Pitfalls

Before changing deployment scripts, read:

- `docs/personal-notes/server-setup-pitfalls.md`

High-risk areas:

- Docker permissions;
- `.env` missing variables;
- Neo4j password length;
- llama-server health endpoint;
- MySQL password and data-volume initialization;
- PowerShell SSH tunnel behavior.
