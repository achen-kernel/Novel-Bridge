# NovelBridge — 新会话快速上手指南

## 项目一句话

API-first 中文古典小说分析管线，Python FastAPI 后端 + 纯前端 HTML/CSS/JS。

## 核心架构

```
用户 → 网页 UI (pipeline.js) → REST API (pipeline_v2.py) → Pipeline 业务层 → MySQL/Qdrant/Neo4j
                                                                   ↕ 本地 9B / DeepSeek API
```

### 三阶段流水线

| 阶段 | 包含 | 模型依赖 | 典型耗时 | 有无 checkpoint |
|------|------|----------|----------|----------------|
| **Stage1** | P1(分章)+P2(梗概) | DeepSeek API(P2) | ~1min | 无（快速） |
| **Stage2** | P3(提取) | 本地 9B(逐chunk) | ~6min/章 | ✅ 逐章 checkpoint |
| **Stage3** | P4(治理)+P5(叙事)+P6(索引)+P7(图谱)+P8(导出) | 本地 9B(P4) | P4~30min,其余~2min | 无（快速） |

## 关键文件

| 文件 | 说明 |
|------|------|
| `app/api/pipeline_v2.py` | **核心 API** — 15+ 端点：checkpoint/stage gate/queue/cleanup |
| `app/pipeline/pipeline_state.py` | **数据层** — `BookPipelineState` + `P3Checkpoint` + `PipelineStateStore` |
| `app/pipeline/fact_pipeline_runner.py` | **P3提取** — 逐章 checkpoint + cancel + 失败检测 + 倒退续跑 |
| `app/pipeline/scheduler.py` | **队列调度** — 批量排队 + 流水线并行 (Stage1不限, Stage2同时1本) |
| `app/pipeline/task_manager.py` | **任务生命周期** — 仅运行时状态，不跨重启 |
| `app/pipeline/extraction_strategy.py` | **提取策略接口** — `Local9BExtraction` + `DeepSeekExtraction`(占位) |
| `app/static/pipeline.js` | **前端** — 三阶段卡片 + 排队面板 |
| `manage_server.py` | **服务管理** — start/stop/restart/status/restart-remote |

## 数据库表

| 表 | 用途 |
|----|------|
| `novel_book_pipeline_state` | 三阶段状态（每本书一行） |
| `novel_p3_checkpoint` | P3 逐章提取结果（book_id + chapter_number 联合主键） |
| `novel_pipeline_task` | TaskManager 持久化（运行时，不跨重启） |

## API 端点速查

### Pipeline 状态
- `GET /api/v2/pipeline/books` — 所有书的三阶段状态 + phase 详情
- `GET /api/v2/books/{id}/pipeline-state` — 单本书的三阶段状态
- `POST /api/v2/books/{id}/pipeline-state/reset?stage=N` — 重置阶段状态（stage 0=全部）

### Stage 2 Checkpoint
- `GET /api/v2/books/{id}/stage2/checkpoint` — 每章 checkpoint 详情
- `POST /api/v2/books/{id}/stage2/resume` — 续跑（倒退2章）
- `POST /api/v2/books/{id}/stage2/retry-chapter/{n}` — 重试单章
- `POST /api/v2/books/{id}/stage2/rerun-all` — 清 checkpoint 全量重跑
- `POST /api/v2/books/{id}/stage2/rebuild-checkpoint` — 从事实数据重建 checkpoint
- `POST /api/v2/books/{id}/stage2/mark-success` — 强制标记阶段二完成

### 阶段闸门
- `POST /api/v2/books/{id}/stage3/force` — 忽略阶段二错误，强制阶段三

### 队列
- `POST /api/v2/pipeline/enqueue` — 批量入队 `{book_ids:[6,9,10],mode:"full"}`
- `POST /api/v2/pipeline/cancel/{book_id}` — 取消某书
- `GET /api/v2/pipeline/queue` — 队列状态
- `POST /api/v2/pipeline/queue/clear` — 清空队列

### 清理
- `POST /api/v2/books/{id}/cleanup/stage1|stage2|stage3` — 阶段级清理
- `POST /api/v2/books/{id}/cleanup` — 全部清理

## 失败处理规则

- 单章重试上限：**5 次** → 永久失败
- 连续失败：**5 章** → 中止整本书
- 总失败率：**>20%** → 中止整本书
- Stage 2 有失败残留 → Stage 3 **阻塞**（可"忽略继续"）
- 取消运行中的 Stage 2 → **保留已完成的 checkpoint**，续跑倒退 2 章

## 已知坑 & 设计决策

### 核心决策
1. **双状态源**：`pipeline_state`（权威）+ `task_manager.phases`（实时 RUNNING 检测）
2. **不跨重启恢复旧任务**：`task_manager.restore()` 已禁用
3. **线程安全**：`asyncio.to_thread` 的任务必须用 `_make_thread_db()` 获得独立 MySQL 连接
4. **前端不依赖进度条**：改用时间+文字状态

### 常见 Bug 模式
1. 新 API 端点加了但前端没调用 → 前端 `computeStageState` 用的是 `phases` 还是 `pipeline_state`？
2. 同步调用忘了 `to_thread` → 服务器卡死
3. cleanup 没清 `task_manager` → 前端显示旧状态
4. dataclass Enum 字段直接传 JSON 字符串 → `str.value` 报错

## 启动命令

```bash
# 本地开发（需要先 SSH 隧道连通远程服务）
python manage_server.py restart-remote   # 重启远程服务（llama + embedding + Docker）
python manage_server.py start            # 开隧道 + 启动本地 18079
python manage_server.py stop             # 停本地
python manage_server.py status           # 查看状态
```

## 当前状态（最后已知）

- ✅ Book 6 西游记：全流程完成
- ✅ Book 9 山海经：全流程完成
- ✅ Book 10 水浒传：阶段一✅ 阶段二✅ 阶段三可能未完成
