# NovelBridge rag-agent

## 目录结构

```
app/
├── api/          HTTP API 端点 (books/browse/eval/facts/frontend/health/qa)
├── pipeline/     预处理管线 P1-P8 (拆章→抽取→治理→叙事→索引→图谱→导出)
├── qa/           问答引擎 (混合检索→LLM 回答)
├── eval/         评估系统 (评测用例→评分→报告)
├── quality/      质量提升工作流 (实体名同步/关系去重/摘要填充)
├── clients/      外部客户端 (MySQL/Qdrant/Neo4j/DeepSeek/llama.cpp/Embedding)
├── stores/       数据访问层 (18个 store)
├── rules/        业务规则
├── schemas/      Pydantic 模型
├── validators/   校验器
├── prompts/      LLM 提示模板
└── utils/        工具函数

scripts/
├── pipeline/     Pipeline 编排脚本
├── check/        数据检查/审计
├── test/         QA 功能测试
├── debug/        诊断/调查
└── ops/          运维操作 (修复/清洗/重索引)
```

## 启动

```powershell
conda activate llamacpp
cd apps/rag-agent
python -m uvicorn app.main:app --host 127.0.0.1 --port 18081
```

## 上传新书

浏览器打开 `http://127.0.0.1:18081/upload` → 选择文件 → 自动拆章

上传后状态为 UPLOADED，不会自动跑 Pipeline。需要手动触发：

```powershell
# P1: 拆 chunk
curl -X POST http://127.0.0.1:18081/api/books/11/process
# P3: 提取
curl -X POST http://127.0.0.1:18081/api/books/11/extract
# P4-P8: 治理、叙事、索引、图谱、导出
```

或一键跑全量：
```powershell
python scripts/pipeline/run_all.py --book-id 11 --phases 3,4,5,7,8
```
