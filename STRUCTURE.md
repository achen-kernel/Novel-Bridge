# NovelBridge 远端目录结构

> 远端已清空，只保留基础设施。
> 你在本地按此结构重建，上传后直接覆盖即可。

## 完整结构

```
/home/wk/novelbridge/
│
├── apps/
│   └── rag-agent/                  ← Python AI Agent（你重写）
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py             ← FastAPI 入口
│       │   ├── api/                ← HTTP 路由
│       │   │   ├── __init__.py
│       │   │   └── ...
│       │   ├── clients/            ← 外部服务客户端
│       │   │   ├── __init__.py
│       │   │   ├── deepseek_client.py
│       │   │   ├── llama_cpp_client.py
│       │   │   ├── mysql_client.py
│       │   │   └── neo4j_client.py
│       │   ├── runners/            ← 业务逻辑/管线 stage
│       │   │   ├── __init__.py
│       │   │   └── ...
│       │   ├── stores/             ← 数据访问层
│       │   │   ├── __init__.py
│       │   │   └── ...
│       │   ├── validators/         ← 输出校验
│       │   │   ├── __init__.py
│       │   │   └── ...
│       │   ├── schemas/            ← Pydantic 请求/响应模型
│       │   │   ├── __init__.py
│       │   │   └── ...
│       │   └── prompts/            ← LLM 提示词模板 (.txt)
│       │       └── ...
│       └── requirements.txt
│
├── deploy/
│   └── remote/                     ← 部署脚本（你重写启动/停止脚本）
│       ├── ports.env               ← ⚠️ 保留，勿删（端口定义）
│       ├── .env                    ← ⚠️ 保留，勿删（密码/API key）
│       ├── nb_up.sh                ← 你要重写
│       ├── nb_down.sh              ← 你要重写
│       ├── nb_healthcheck.sh       ← 你要重写
│       ├── docker-compose.yml      ← 你要重写
│       └── schema.sql              ← 你要重写（建表语句）
│
├── scripts/                        ← 运维脚本（你重写）
│   └── remote/
│       ├── run_pipeline.py
│       └── nb_log.sh
│
├── docs/                           ← 文档（你重写）
│   └── ...
│
├── training/                       ← 9B 训练
│   ├── LLaMA-Factory/              ← ⚠️ 保留，已装好
│   └── data/                       ← 训练数据（你重新生成）
│       ├── train/
│       ├── dataset_info.json
│       └── ...
│
├── models/                         ← ⚠️ 模型文件，保留
│   ├── qwen3.6-35b-gguf/           ← 35B 模型 (~35GB)
│   │   └── Qwen_Qwen3.6-35B-A3B-Q8_0.gguf
│   └── Qwen3.5-9B/                 ← 9B 模型 (~19GB)
│       └── ...
│
├── data/                           ← ⚠️ Docker 数据卷，保留
│   ├── mysql/
│   └── neo4j/
│
├── env/                            ← conda 环境（你用到的）
├── runtime/                        ← 运行时 PID 文件
└── logs/                           ← 日志（运行时自动创建）
```

## 端口固定定义（不要改，否则要同步改 Java 端）

`deploy/remote/ports.env` 中定义：

```
MYSQL_PORT=13306
NEO4J_HTTP_PORT=17474
NEO4J_BOLT_PORT=17687
LLAMA_PORT=18080
RAG_AGENT_PORT=18081
QDRANT_PORT=16333
```

## 本地→远端上传覆盖

你在本地按上面目录结构建好项目后：

```bash
# 在本地上打包
tar czf novelbridge.tar.gz apps/ deploy/ scripts/ docs/

# 传到远端
scp novelbridge.tar.gz user@remote-server-ip:/home/wk/novelbridge/

# 在远端解压覆盖
ssh user@remote-server-ip "cd /home/wk/novelbridge && tar xzf novelbridge.tar.gz"
```

## 当前远端存活服务

| 服务 | 状态 | 端口 | 启动方式 |
|---|---|---|---|
| MySQL | ✅ 运行中 | 13306 | Docker |
| Neo4j | ✅ 运行中 | 17687/17474 | Docker |
| llama-server | ❌ 已停 | 18080 | 需你重写 nb_up.sh 后启动 |
| rag-agent | ❌ 已停 | 18081 | 需你先上传 Python 代码 |

所有启动脚本（`nb_up.sh` 等）已删除，需要你重写。重写后：

```bash
bash /home/wk/novelbridge/deploy/remote/nb_up.sh
```

即可恢复全部服务。
