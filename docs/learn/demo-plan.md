# NovelBridge Demo Plan

当前策略：先做一个可运行的 walking skeleton，再逐步硬化。不要先实现完整 20 表和完整前端。

## Demo 路线

| 轮次 | 用户可见闭环 | 真实实现 | Mock/债务 | 验收证据 | 状态 |
|---|---|---|---|---|---|
| Demo 0 | 设计收口 | 表设计分层、skill 适配、状态文件 | 不写业务代码 | `vtl_status.py`、`vtl_scan.py` 能正确识别状态和后端根目录 | completed |
| Demo 1 | 导入样例书并保存章节 | Spring Boot API + MySQL 保存 Book/Chapter | 切章可先用简单规则；无前端 | Maven test + API 调用 + 数据库记录（100 chapters） | completed |
| Demo 2 | 构建任务可追踪 | AgentRun/AgentStep 记录导入/切章/保存步骤 | 暂不接 Python RAG | 失败和成功都能查询状态/errorMessage | in_progress |
| Demo 3 | 最小问答带引用 | ChatSession/ChatMessage/Citation；关键词检索章节 | 可先不接 LLM，用模板回答 | 提问返回答案和 chapter 引用 | planned |
| Demo 4 | 最小三栏工作台 | 左侧书籍，中间问答，右侧引用 | UI 可简陋；无复杂审核 | 浏览器可完成一次问答并看到引用 | planned |
| Demo 5 | 替换关键 mock | 接 Python 切章、chunk、模型抽取 | Chroma/FTS 可分步接入 | 样例书完整构建并可追溯问答 | planned |

## Demo 核心表

Demo 1-3 只需要：

```text
novel_book
novel_chapter
novel_chunk
novel_chapter_fact
novel_agent_run
novel_agent_step
novel_model_run
novel_chat_session
novel_chat_message
novel_citation
```

`novel_user`、`novel_project`、`novel_folder` 可以先用默认用户/默认项目简化，等 Demo 4 前再补完整管理。

## 债务清单

| 来源轮次 | 债务 | 为什么允许 | 何时硬化 | 状态 |
|---|---|---|---|---|
| Demo 1 | 简单切章规则（正则 `第X回`） | 先验证导入和持久化链路 | Demo 5 接 Python splitter | active |
| Demo 3 | 模板回答或 mock LLM | 先验证 Chat/Citation 数据链路 | Demo 5 接本地模型 | planned |
| Demo 1-3 | 默认用户/项目 | 降低早期表和权限复杂度 | Demo 4 前补 User/Project/Folder | planned |

## 完成红线

- 没有 `AgentRun/AgentStep`，不算完成构建。
- 没有 `Citation`，不算完成问答。
- 没有 errorMessage，失败路径不算完成。
- 没有可重复验证命令或手工步骤，不关闭阶段。
