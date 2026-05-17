# rag-agent

NovelBridge 的 Python 模型编排服务。

## 本地路径 vs 远程路径

| 本地 | 远程 |
|---|---|
| `rag-agent/`（项目根） | `/home/wk/novelbridge/apps/rag-agent/` |

部署到远程服务器时，整个目录内容放到 `apps/rag-agent/` 下。
上传后执行 `run.sh` 即可启动。

## 快速启动

```bash
pip install -r requirements.txt
python -m app.main --port 18081
```

## API

| 端点 | 说明 |
|---|---|
| `GET /health` | 聚合健康检查 |
| `GET /health/llm` | llama-server 健康 |
| `GET /health/mysql` | MySQL 健康 |
| `GET /health/neo4j` | Neo4j 健康 |
| `GET /health/vector` | Chroma 健康（mock） |
| `POST /extract/entities` | 实体抽取（Demo 5B） |
