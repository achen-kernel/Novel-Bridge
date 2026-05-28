# NovelBridge 代码重构方案

> 目标：更健壮、更简洁、更可读、更容易扩展，流程更可控。
> 当前问题：前后端耦合、错误处理脆弱、无幂等性、JS 模板难维护、任务管理无持久化。

---

## 一、核心问题清单

### 1. 前后端紧耦合
- **f-string 内嵌 HTML/JS** — `frontend.py` 和 `demo.py` 用 Python f-string 写整个前端页面
- **后果**：JS 语法错误无法被静态检测、编辑时容易产生重复函数、引号转义地狱
- **目标**：前后端分离，至少把 HTML/CSS/JS 放到独立文件

### 2. 管线无幂等性
- P1/P3 写入时 UNIQUE KEY 冲突直接崩溃
- 重跑必须手动清数据，没有自动 upsert 机制
- **目标**：全量/增量重跑都能安全执行

### 3. 错误处理不统一
- 后台任务异常靠 `task_manager.launch()` 的 try/except 兜底
- 部分错误信息进入日志但不进任务状态
- P5/P3 等阶段的 Python 对象传参类型不匹配
- **目标**：统一错误模型 + 结构化错误记录

### 4. TaskManager 无持久化
- 重启后丢失所有任务状态
- 无法追踪历史执行记录
- **目标**：至少轻度持久化（SQLite 或 MySQL 表）

### 5. 前端 JS 维护困难
- 所有 JS 写在 Python 字符串中
- 多次编辑后产生重复函数、死代码
- **目标**：JS 从 Python 代码中分离

### 6. 模型调用管理混乱
- `use_model` / `provider` 参数分散在不同层级
- DeepSeek 和 9B 的 fallback 链不清晰
- **目标**：统一模型抽象层

### 7. 服务管理原始
- `manage_server.py` 靠 netstat/psutil 找进程
- Windows 下端口释放不及时
- **目标**：可靠的启动/停止/健康检查

---

## 二、重构方案

### Phase A：前后端分离（高优先级，风险可控）

**改动文件**：
- `app/api/frontend.py` → 移除 `PIPELINE_HTML` 字符串，改为读取 HTML 文件
- `app/api/demo.py` → 同上
- 新建 `app/static/` 目录存放 HTML/CSS/JS

**具体做法**：

```
apps/rag-agent/app/static/
├── pipeline.html          # 流水线页面 HTML
├── pipeline.js            # 流水线页面 JS
├── pipeline.css           # 流水线页面 CSS
├── demo.html              # Demo 页面
├── demo.js                # Demo 页面 JS
├── demo.css               # Demo 页面 CSS
└── shared.js              # 公共函数 (esc, $, 等)
```

Python 端改为：
```python
@router.get("/pipeline", response_class=HTMLResponse)
async def pipeline_page():
    html = Path("app/static/pipeline.html").read_text(encoding="utf-8")
    return HTMLResponse(html)
```

**优势**：
- JS 语法错误可以直接被编辑器/ESLint 检测
- 编辑 HTML 不需要修改 Python 代码
- 多人协作时可以独立修改前端

### Phase B：Pipeline 幂等性（中优先级，核心架构）

**改动文件**：
- `app/pipeline/chapter_fact_store.py` — 插入改为 INSERT ... ON DUPLICATE KEY UPDATE
- `app/pipeline/chunk_store.py` — 同上
- `app/api/pipeline_v2.py` — `_run_p1` / `_run_p3` 使用 upsert 逻辑

**核心改动**：

在 `chapter_fact_store.py` 中：
```python
def insert_fact(self, ..., chapter_id):
    sql = """
        INSERT INTO novel_chapter_fact (...) VALUES (...)
        ON DUPLICATE KEY UPDATE fact_json=VALUES(fact_json), updated_at=NOW()
    """
```

在 `pipeline_v2.py` 的 `_run_p1` 中：
```python
# 跳过 chapter 创建（UNIQUE 冲突时自动跳过）
INSERT IGNORE INTO novel_chapter ...
```

**优势**：
- 全流程/重跑不再卡在 P1/P3
- 不需要手动清数据
- 增量更新安全

### Phase C：统一错误模型（中优先级）

**改动文件**：
- 新建 `app/pipeline/errors.py` — 定义 PipelineError 层级
- 修改 `task_manager.py` — 结构化错误记录
- 修改 `pipeline_v2.py` — 各 `_run_p*` 使用统一错误模型

**设计**：
```python
class PipelineError(Exception):
    def __init__(self, phase: str, book_id: int, code: str, message: str, detail: dict = None):
        self.phase = phase
        self.book_id = book_id
        self.code = code  # "FK_CONSTRAINT", "DB_CONNECTION", "MODEL_FAILURE"
        self.message = message
        self.detail = detail or {}
```

```python
# 在 task_manager.py 中增加结构化错误记录
class PipelineTask:
    ...
    error_code: str = ""
    error_detail: dict = {}
```

```
前端渲染时：
  FAILED → 显示 error_code 和简短 message
  详细错误折叠在详情面板中
```

**优势**：
- 前端可以针对不同错误码显示不同 UI
- 调试时可以通过 error_code 快速过滤
- 避免把 Python traceback 直接暴露到前端

### Phase D：任务持久化（中优先级，可选）

**改动文件**：
- 新建 `app/stores/task_store.py` — Task 的 MySQL 存储
- 修改 `task_manager.py` — TaskManager 改为可选持久化

**设计**：
```python
class TaskStore:
    def save(task: PipelineTask): ...
    def find(task_id: str): ...
    def list_by_book(book_id, phase): ...
```

`TaskManager` 同时维护内存 dict + MySQL 持久化。启动时从 MySQL 恢复最近 100 条任务。

**优势**：
- 重启后任务历史不丢失
- 可以查看历史执行记录

### Phase E：统一模型抽象层（低优先级）

**改动文件**：
- 新建 `app/clients/model_client.py` — 统一模型调用接口
- 修改 `extraction_runner.py` — 使用 ModelClient 而不是直接调 llama/deepseek

**设计**：
```python
class ModelClient:
    def __init__(self, provider: str = "local"):
        self.provider = provider  # "local" | "deepseek"
    
    async def chat(self, messages, **kwargs):
        if self.provider == "deepseek":
            return await deepseek_client.chat(messages, **kwargs)
        else:
            return await llama_client.chat(messages, **kwargs)
    
    async def chat_json(self, messages, **kwargs):
        """统一的 JSON 输出调用，自动处理 GBNF grammar / no grammar"""
        if self.provider == "deepseek":
            return await deepseek_client.chat_json(messages, **kwargs)
        else:
            return await llama_client.chat_json(messages, grammar=load_grammar(), **kwargs)
```

**优势**：
- 新增 provider（如 GPT-4、Claude）只需要加一个分支
- 统一处理 fallback 链
- 统一记录 model_call 日志

### Phase F：服务管理优化（低优先级）

**改动文件**：
- `manage_server.py` — 改为使用 pidfile + 信号
- 新建 `manage_server.bat` — Windows 一键脚本（纯英文，ANSI 编码）

**设计**：
```python
# 启动时写 pidfile
PID_FILE = "server.pid"
def start():
    proc = subprocess.Popen([...])
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

def stop():
    if os.path.exists(PID_FILE):
        pid = int(open(PID_FILE).read())
        os.kill(pid, signal.SIGTERM)
        os.remove(PID_FILE)
```

**优势**：
- 不需要依赖 netstat/psutil
- 跨平台一致

---

## 三、执行顺序

```
Phase A ──── 前后端分离（2-3h）
    │
    ▼
Phase B ──── Pipeline 幂等性（1-2h）
    │
    ▼
Phase C ──── 统一错误模型（1h）
    │
    ▼
Phase D ──── 任务持久化（1-2h，可选）
    │
    ▼
Phase E ──── 统一模型抽象（1h，可选）
    │
    ▼
Phase F ──── 服务管理优化（0.5h）
```

---

## 四、约定与约束

### 约定
1. **所有新文件使用 `.py`、`.html`、`.js`、`.css` 独立文件，不内嵌在 Python 字符串中**
2. **所有 SQL 操作使用 upsert（`ON DUPLICATE KEY UPDATE`），不做先删后插**
3. **所有错误使用结构化 PipelineError，不裸抛 Exception**
4. **所有模型调用通过 ModelClient 统一接口**
5. **所有 JS 函数名全局唯一，用 `grep` 检查重复**
6. **前端不要 `await` 在非 async 函数中，用 ESLint 检查**
7. **每个页面有统一的导航栏**

### 不做的
- ❌ 不换前端框架（React/Vue），保持 vanilla HTML/CSS/JS
- ❌ 不换 Python 后端框架
- ❌ 不重新设计数据库 schema
- ❌ 不增加新的外部依赖
- ❌ 不改动 Java 代码

### 验收标准
| 标准 | 验证方式 |
|------|----------|
| JS 文件可以被 ESLint 静态检查 | 运行 ESLint 0 error |
| P1-P8 可以安全重跑（不报 UNIQUE 错误） | 对同一本书连续跑两次全流程 |
| 错误在前端显示可读信息（不是 Python traceback） | 关掉 MySQL 后触发 P3，前端显示"数据库连接失败" |
| 重启后任务历史不丢失 | 重启前记录 task_id，重启后 GET /api/v2/tasks/{id} 返回 |
| 前后端分离 | 修改 pipeline.js 不需要重启 uvicorn |
| 启动/停止脚本可以在任意目录执行 | 在桌面执行 `python path/to/manage_server.py start` |

---

## 五、Prompt 给新 Agent 使用

```
你是 NovelBridge 项目的重构专家。

当前代码库：
- 根目录 [project-root]
- 核心代码 [project-root]\apps\rag-agent

请按照 docs/refactor-plan.md 的 Phase A → B → C → D → E → F 顺序执行重构。

每个 Phase 完成后：
1. 验证所有修改的文件语法正确（python -B -m py_compile）
2. 验证前端页面可以正常渲染（curl /pipeline）
3. 验证管线阶段可以触发（curl POST /api/v2/books/6/phase/P1）
4. 记录修改文件清单

约束：
- 不改数据库 schema
- 不改 Java 代码
- 保持 vanilla JS（不用 React/Vue）
- 前后端分离后的 HTML/JS/CSS 放在 apps/rag-agent/app/static/
- 不要内嵌 HTML 在 Python 字符串中
```

---

## 六、已知陷阱与经验教训（2026-05-27 重构实录）

### 1. 前后端分离 — 静态文件托管

**问题**：HTML/CSS/JS 从 Python f-string 移到 `app/static/` 后，页面空白/无样式。

**根因**：
- FastAPI **不会自动托管** `static/` 目录。需要显式 `app.mount("/static", StaticFiles(...))`。
- HTML 中的引用的路径 `href="static/xxx.css"` 是**相对路径**，在 `/browse/` 等子路径下解析为 `/browse/static/xxx.css` → 404。必须用**绝对路径** `/static/xxx.css`。

**修复**：
```python
# main.py
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="app/static"), name="static")
```
所有 `<link>` 和 `<script>` 的 `href`/`src` 用 `/static/xxx.css` 而非 `static/xxx.css`。

### 2. JS 占位符替换陷阱

**问题**：Demo 页面书籍列表、参考问题空白，项目/会话按钮无反应。

**根因**：
- 原 `demo.py` 的 `HTML_TEMPLATE` 是一个 Python f-string，内含 `Q_JSON_PLACEHOLDER` 和 `B_JSON_PLACEHOLDER` 占位符。
- `demo_page()` 用 `html.replace("Q_JSON_PLACEHOLDER", _Q_JSON)` 替换为真实 JSON 数据。
- 重构后，JS 被分离到 `static/demo.js`。但 `demo.js` 文件由 FastAPI 的 `StaticFiles` 直接服务，**不经过 Python 处理**，所以里面的 `Q_JSON_PLACEHOLDER` 字面量不会被替换。
- 浏览器执行到 `var NB_Q = Q_JSON_PLACEHOLDER;` 时，`Q_JSON_PLACEHOLDER` 是未定义变量 → `ReferenceError` → 整个 `<script>` 停止执行 → 后续渲染、健康检查、API 调用全挂。

**修复**：
- 占位符替换**必须在 HTML 层面完成**（HTML 由 Python 渲染）。
- `demo.html` 中用内联 `<script>` 设置 `NB_Q` 和 `NB_B`（被 Python 替换）。
- `demo.js` 只引用全局变量 `NB_Q`、`NB_B`，不再包含占位符。

**规则**：
> `static/` 下的 JS/CSS 文件是纯静态资源，不经过服务端模板引擎处理。
> 任何需要服务端替换的内容（API Key、JSON 数据、配置标记）必须在 HTML 层面注入。

### 3. 服务不可用 vs 前端 bug

**问题**：重构后 MySQL/Qdrant/Neo4j/9B/Embed 健康检查全红。

**分析**：健康检查调用 `/health/mysql` 等后端 API。如果本地没跑这些服务，返回非 200 → 红点。**这是正常行为，不是重构引入的 bug。** 重构前后行为一致。

**教训**：区分"前端渲染错误"和"后端服务不可用"。JS 崩溃会导致所有后续操作失效，容易掩盖真正的后端状态。

### 4. ON DUPLICATE KEY UPDATE 的 lastrowid 陷阱

**问题**：Pipeline P1 分章后构建 chunks 时外键约束失败（`fk_chunk_chapter`）。

**根因**：
- `chapter_store.insert_chapter()` 使用 `INSERT ... ON DUPLICATE KEY UPDATE`。当遇到重复 key（已存在的 `(book_id, chapter_number)`），MySQL 执行 UPDATE 而非 INSERT，此时 `cursor.lastrowid` 返回 **0**。
- 后续 `chunk_store.insert_chunk()` 使用这个 **chapter_id=0** 去插入 `novel_chunk`，触发外键 `fk_chunk_chapter` 约束失败。
- 触发条件：数据没清干净（旧 chapter 残留）+ upsert 遇到重复 → `lastrowid=0`。

**修复**：
1. 彻底清理数据时用 `SET FOREIGN_KEY_CHECKS=0` + `DELETE FROM ... WHERE book_id=?` + `SET FOREIGN_KEY_CHECKS=1`
2. 或者 `ON DUPLICATE KEY UPDATE` 后额外查询一次来获取真实 id：`SELECT id FROM novel_chapter WHERE book_id=? AND chapter_number=?`

**教训**：
> `ON DUPLICATE KEY UPDATE` 后 `lastrowid` 不可信赖——INSERT 路径返回新 id，UPDATE 路径返回 0。
> 如果需要后续引用，必须在 upsert 后重新查询获取真实 id。

### 5. MysqlClient 共享连接 + 线程池冲突

**问题**：`BookProcessor.process()` 在 `run_in_executor` 线程池中运行时，MySQL 外键约束间歇性失败。

**根因**：
- `MysqlClient.connect()` 返回**单例共享连接**。当主线程（处理 HTTP 请求）和线程池线程（执行 P1）同时使用这个连接时，出现竞争条件。
- 一个线程的游标操作（INSERT）可能被另一个线程的查询干扰，导致 `lastrowid` 混乱或事务隔离问题。
- 同步执行（去掉 `run_in_executor`）后问题消失。

**修复**：
- `MysqlClient` 新增 `new_connection()` 方法，每次都返回独立连接。
- `BookProcessor` 使用 `new_connection()` 并在 `finally` 中 `close()`。

**教训**：
> MySQL 连接不是线程安全的。线程池任务必须使用独立连接，不能共享主线程的连接。

### 6. 清理脚本不完整导致外键连锁失败

**问题**：清理派生数据的脚本漏了 `novel_agent_run`、`novel_agent_step` 表，导致 P1 创建 AgentRun/Step 时外键约束失败。

**根因**：
- 首次清理只删了核心数据表（chapter/chunk/fact 等），没删 `novel_agent_run`（558 行）和 `novel_agent_step`（4980 行）。
- `BookProcessor.create_run()` 插入新 run，但 `create_step()` 引用这个 run 时因某些残留 FK 关系失败。

**修复**：
- 完整清理脚本按外键依赖顺序删除所有派生表：`agent_step → agent_run → chapter_fact → chunk → chapter → ...`
- 对于顽固残留，用 `SET FOREIGN_KEY_CHECKS=0` + `DELETE FROM all tables` + `SET FOREIGN_KEY_CHECKS=1`。

**教训**：
> MySQL 清理必须按外键顺序执行，子表先删、父表后删。
> 任何遗漏的表都可能因为 FK 约束导致看起来无关的操作失败。

### 7. Pipeline 状态三层同步问题

**问题**：流水线页面显示"提取还在运行，后面的治理/索引/叙事已完成"的虚假状态。批量运行中途消失。

**根因**：
- Pipeline 状态维护在**三个独立层**：内存 `task_manager`（Python dict）+ MySQL `novel_pipeline_task` 表 + 前端 UI 轮询。
- 当新全流程启动时，P1 触发新任务 → P1 显示 RUNNING/SUCCESS，但 P4-P8 还没触发新任务 → 显示**上周旧任务的 SUCCESS**。
- 清理按钮只清数据不清任务 → `task_manager` 内存中残留旧成功记录。
- 批量运行（`batchRun`）循环内 `fullPipeline` 未正确处理异常链路，某阶段超时/失败后未正确传递。

**修复**（三个层面）：
1. **后端 API**：`/api/v2/pipeline/books` 检测到某本书**有任何 RUNNING 任务**时，其他非 RUNNING 阶段全部显示 `PENDING`，不再显示旧 SUCCESS。
2. **清理联动**：`POST /books/{id}/cleanup` 时同时调用 `task_manager.clear_by_book(book_id)` + 删除 `novel_pipeline_task`。
3. **全流程前端**：`fullPipeline()` 开始时对所有阶段设为 `排队中...` + 调 `DELETE /books/{id}/tasks`。
4. **新增取消全流程按钮**：红色按钮，设置 `_cancelFullPipeline=true`，`waitTask` 轮询中检测到后退出。

**教训**：
> 分布式状态（内存 + DB + 前端）必须有一致的生命周期管理。
> 清理操作必须清理所有相关状态层，否则残留数据导致误导性 UI。
> 用户看到的"最新状态"必须结合"是否有任务正在运行"来判断，不能只看最新一条任务记录。

### 8. 前端 Cancel 按钮的 task_id 获取方式

**问题**：全流程运行时每个阶段旁边的 ✕ 取消按钮点了没反应。

**根因**：`cancelTask()` 从 `BOOKS_DATA`（轮询更新的全局变量）读取 `latest_task_id`，但全流程运行期间 `BOOKS_DATA` **不刷新** → `taskId=null`。

**修复**：取消按钮 `<button id="cancel-{bookId}-{phase}">` 上存 `data-task-id` 属性，`pollTask()` / `waitTask()` / `triggerPhase()` 启动时写入，`cancelTask()` 直接从 DOM 读取。

**教训**：
> 不要依赖异步更新的全局变量来获取关键数据。DOM 属性在事件触发时是同步可读的，更可靠。

### 9. P3 提取极慢（本地 9B 模型）

**问题**：P3（实体/关系/事件提取）在本地 9B 模型上每章耗时约 90-150 秒，搜神记 35 章耗时 **87 分钟**。

**根因**：
- 每章包含多个 chunk，每个 chunk 都调一次本地 9B 模型
- 通过 SSH 隧道的 llama-server 延迟较高
- 35 章 × 多 chunks = 大量串行模型调用

**当前限制**：
- 默认 `waitTask` 超时 20 分钟（600 次 × 2秒），P3 很容易超时
- `_run_books.py` 脚本已设为 3 小时超时

**缓解**：
- 增大 P3 轮询超时到 3 小时
- `FactPipelineRunner` 每章前 `conn.ping(reconnect=True)` 保持 MySQL 连接
- 使用独立连接 `new_connection()` + `finally close()`

**注意**：
> P3 是流水线中最慢的阶段，不是 bug，而是本地模型推理的计算约束。
> 如果需要加速：使用 DeepSeek API 做提取（更快但更贵），或增加本地 GPU 推理能力。

### 10. 配置保存时密钥被空字符串覆盖

**问题**：配置页面密码框对掩码值显示为 `""`（空），用户没重新输入就保存 → 空字符串覆盖真实 API Key/密码。

**根因**：
- 前端 GET `/api/config` 返回的密钥是掩码值（如 `sk-****abcd`）
- 前端密码框检测到 `*` → `displayVal = ""`
- 用户点保存时未修改 → 传 `api_key: ""` → 后端保存空字符串

**修复**：
- **后端**：`save_config` 中 `if not value or "*" in str(value)` → 保留旧值
- **前端**：密码框显示 `•••••••• (已设置)` 占位符提示用户已有值

**教训**：
> 配置的"读-改-写"流程中，密钥类字段必须特殊处理——前端不能把掩码值发回后端覆盖真实值。

### 11. QA 检索跨书污染

**问题**：问搜神记的问题（"董永和七仙女故事讲了什么？"），QA 返回了西游记的内容。

**根因**（两层）：
1. **检索层**：`retrieval_runner.py` 的 `hybrid_search()` 在 book_id 过滤无结果时，fallback 到 `book_id=None` 搜所有书 → 从西游记里找到"七仙女"。
2. **QA 层**：`qa_runner.py` 的 Retrieval Quality Gate 在检索为空时直接返回固定文字（跳过 LLM），而不是让模型用自己的知识回答。

**修复**：
- **检索层**：移除跨书 fallback，搜不到就返回空。
- **QA 层**：检索为空时改用 `model_knowledge_prompt` 让 DeepSeek 用自己的知识回答，并注明"（基于模型知识）"。

**教训**：
> "检索不到当前书的内容" ≠ "去别的书找内容"。跨书搜索的假设是危险的——不同书的实体名可能相同但含义完全不同。
> LLM 的知识回退比跨书搜索结果更可靠。

---

### 12. Pipeline 三阶段重构的坑（Phase 0-5）

**背景**：将 P1-P8 平铺的 8 个阶段重构为三阶段（Stage1=P1+P2, Stage2=P3, Stage3=P4-P8），加上逐章 checkpoint、队列调度、前端重写。

**1. 旧 task_manager 残留任务导致状态假死**

**问题**：重启后 Book 6 的 P3 显示 RUNNING，找不到停止按钮，其他服务被阻塞。

**根因**：
- `task_manager.restore()` 从 `novel_pipeline_task` 表恢复了旧 RUNNING 任务
- 前端 `computeStageState()` 用 `book.phases`（task_manager 数据）计算阶段状态
- 旧任务在 task_manager 内存中显示 RUNNING，但实际的 asyncio 协程早就不在了
- `cancel-hard` 端点只能发信号（event.set()），但没有协程在监听

**修复**：
- 新增 `pipeline-state/reset` 端点 — 重置任意书的任意阶段状态
- `cancel-hard` 端点实际写入 cancel event + 标记 CANCELLED
- 前端 `computeStageState()` 改为优先用 `book.pipeline_state`（新表），降级到 `book.phases`
- 重启后统一重置所有书的 state：`POST /api/v2/books/{id}/pipeline-state/reset?stage=0`

**教训**：
> 从 MySQL 恢复旧任务到内存是危险的——旧任务的对象状态不能反映实际运行状态。
> 新旧架构共存期，前端必须明确区分用哪个数据源，不能混用。

**2. 前端 JS 语法错误导致整个页面白屏**

**问题**：流水线页面显示"加载中..."，控制台报 `Uncaught SyntaxError: Unexpected token '}'` 和 `loadPipeline is not defined`。

**根因**：
- 通过 `edit` 工具替换 `fullPipelineResume` 函数时，旧代码被部分保留（多出 ~20 行 try/catch 残留）
- 残留代码含 3 个额外 `}` 和 1 个额外 `(`
- JS 解析失败 → 所有函数名未注册 → `onclick="loadPipeline()"` 报 `not defined`

**修复**：
- 用 `node` 脚本扫描大括号平衡性：`Final brace depth: 0, paren depth: 0` 才是干净的
- 删掉残留的 try/catch 块

**教训**：
> 用 `edit` 做代码替换时，必须确认 oldString 有足够的上下文来唯一定位。
> JS 无编译期检查，一个语法错误就会让整个应用白屏。修改后务必做 basic syntax checks。

**3. API_BASE 端口配置不匹配**

**问题**：书库页面显示 "error"，`frontend.py` 的 `_get_json()` 抛异常。

**根因**：
- `frontend.py:20` 定义 `API_BASE = "http://127.0.0.1:18081"`
- `manage_server.py` 只启动一个 uvicorn 实例在端口 **18079**
- `_get_json("/api/books")` 尝试连接 `127.0.0.1:18081`（不存在）→ 超时 → 被 except 捕获显示 error
- 这个 18081 是远程服务器上另一个 rag-agent 实例的端口（SSH tunnel 转发到远程的 18081），本地开发时不会启动

**修复**：
- 改 `API_BASE = "http://127.0.0.1:18079"`（和 manage_server.py 一致）

**教训**：
> 代理调用的目标端口必须和实际启动的服务端口一致。本地开发环境只有一个 uvicorn 进程（18079），不能硬编码远程的 18081。
> 这种"自调用"架构（frontend 通过 HTTP 调自己的 API）本身就脆弱——一个更好的方案是直接调用 Python 函数而非 HTTP。

**4. 前端使用旧 book.phases 而不是新的 pipeline_state**

**问题**：即使 `pipeline_state` 表里 Status=PENDING，前端阶段二仍然显示 RUNNING（因为 task_manager 里有旧 SUCCESS/CANCELLED 记录）。

**根因**：
- 设计师写的 `computeStageState()` 使用 `book.phases`（来自 task_manager 的 8 个阶段状态）
- `pipeline_state` 虽然已经正确返回（PENDING），但前端根本没用这个数据

**修复**：
- `computeStageState()` 优先读 `book.pipeline_state`，降级到 `book.phases`

**教训**：
> 前后端数据源必须一一对应。后端新增了 `pipeline_state` 字段但前端没消费它 → 等于没加。
> 前端在计算阶段状态时应该用后端的阶段级聚合结果，而不是自己从阶段级数据重新计算。

**5. `fullPipelineResume` 使用错误的 enqueue mode**

**问题**：`fullPipelineResume` 调用 `POST /api/v2/pipeline/enqueue` 时传 `mode: 'resume'`，但后端只支持 `full|stage1|stage2|stage3`。

**根因**：
- 设计师写了 enqueue 调用，但 `mode: 'resume'` 是设计师自己想的一个模式，后端不支持
- 返回 `d.status === 'queued'` 检查失败（后端返回 `status: 'ok'`）
- 但代码有 fallback，所以功能勉强可用

**修复**：
- 去掉 enqueue 调用（单本书连续跑不需要排队），直接按阶段状态判断该跑哪些 phases
- 用 `pipeline_state` 判断已完成的阶段，跳过

**教训**：
> 前端和后端的 API 契约必须对齐。新增前端调用前至少要确认后端有没有这个端点/参数。
> 设计师写的代码需要 review API 调用的正确性。

---

## 六、Pipeline 架构总结（v2 设计）

### 数据流

```
用户操作 → 前端(pipeline.js) → REST API(pipeline_v2.py)
                                         │
                           ┌─────────────┼─────────────┐
                           ▼             ▼             ▼
                    PipelineStateStore  TaskManager  Scheduler
                    (book_pipeline_     (phase-level  (queue +
                     state + p3_check    task          pipelined
                     point)             lifecycle)    execution)
                           │             │             │
                           ▼             ▼             ▼
                                    MySQL (novel_book_pipeline_state,
                                           novel_p3_checkpoint,
                                           novel_pipeline_task)
```

### 三阶段生命周期

| 阶段 | 包含 | 数据表 | 模型依赖 | 典型耗时 |
|------|------|--------|----------|----------|
| Stage 1 | P1(分章) + P2(梗概) | `novel_chapter`, `novel_chunk` | DeepSeek API(P2) | ~1min |
| Stage 2 | P3(提取) | `novel_chapter_fact`, `novel_model_call` | 本地 9B(逐 chunk) | ~2-4h/100章 |
| Stage 3 | P4-P8(治理/叙事/索引/图谱/导出) | `novel_entity_*`, `novel_relation_*`, Qdrant, Neo4j | 本地 9B(P4) | ~5min |

### 失败处理规则

- 单章重试上限：5 次 → 标记永久失败
- 连续失败阈值：5 章 → 中止整本书
- 总失败率阈值：>20% → 中止整本书
- Stage 2 有残留失败 → Stage 3 默认阻塞，用户可「忽略继续」
- 取消运行中的 Stage 2 → 保留已完成的章，续跑从断点接上

---

## 七、待办清单

| 优先级 | 任务 | 状态 |
|--------|------|------|
| 🔴 高 | Pipeline 状态三层同步修复 | ✅ 已修复 |
| 🔴 高 | Cancel 按钮点击无反应 | ✅ 已修复 |
| 🔴 高 | P3 超时/连接断开 | ✅ 已缓解（3h 超时 + ping） |
| 🟡 中 | "清全部"按钮后前端状态不重置 | ❌ 待修复 |
| 🟡 中 | QA 检索跨书污染 | ✅ 已修复 |
| 🟡 中 | 空检索 skip LLM → 改走模型知识 | ✅ 已修复 |
| 🟢 低 | P3 加速（DeepSeek API 提取） | ❌ 待评估 |
| 🟢 低 | KnowledgePatch 前端审核页面 | ❌ 待开发 |
| 🟢 低 | Java facade 产品 API 聚合 | ❌ 待开发 |

## 八、关键文件清单

| 文件 | 当前问题 | 重构方向 |
|------|----------|----------|
| `app/api/frontend.py` | HTML 在 f-string 内 | 移出到 static/ 目录 |
| `app/api/demo.py` | HTML 在 f-string 内 | 移出到 static/ 目录 |
| `app/api/pipeline_v2.py` | 错误处理不规范 | 使用 PipelineError |
| `app/pipeline/task_manager.py` | 无持久化 | 加 MySQL 持久化 |
| `app/pipeline/chapter_fact_store.py` | 无 upsert | 加 ON DUPLICATE KEY UPDATE |
| `app/pipeline/fact_pipeline_runner.py` | provider 透传不干净 | 使用 ModelClient |
| `app/clients/llama_cpp_client.py` | 和 deepseek_client 各走各路 | 统一到 ModelClient |
| `manage_server.py` | netstat 依赖 | 改为 pidfile |
| `start_novelbridge.bat` | 编码问题 | 删掉，用 manage_server.py |
| `stop_novelbridge.bat` | 同上 | 删掉 |
