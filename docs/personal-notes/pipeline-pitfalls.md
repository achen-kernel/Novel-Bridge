# Pipeline 部署与运维坑点记录

## 18. Qwen3.5 llama-server chat completion empty content

Symptom:

- `/v1/chat/completions` returns an empty `message.content`.
- ReaderAgent answer mode can reach QA, but generated answer is empty or unusable.

Fix:

```bash
--chat-template-file /home/wk/novelbridge/models/Qwen3.5-9B/chat_template.jinja
--jinja
--reasoning off
```

Keep `deploy/remote/nb_up.sh`, `deploy/remote/nb_remote.sh`, and `scripts/remote/start_llama.sh` aligned on these flags.

## 1. llama-server 上下文长度不足导致 400

**现象**: 模型提取时部分 chunk 返回 `400 Bad Request`，回退到规则模式，导致那些 chunk 没有关系/事件抽取。

**原因**: `--ctx-size` 默认 8192 tokens。对于含 prior_hint 角色名+别名+entity_focus 的提取 prompt，加上 chunk 原文（800-1500 字 ≈ 2000 tokens），加上 8192 tokens 的输出限制，容易超限。

**修复**: 
- `.env` 中设置 `LLAMA_CTX_SIZE=65536`
- `start_llama.sh` 读取环境变量
- 同时设置 `--batch-size 2048 --ubatch-size 2048` 优化吞吐

**教训**: 本地模型上下文一定要根据实际 prompt 大小评估后再设，不能沿用默认值。9B Q8_0 模型 + 65536 ctx 约用 18GB 显存（权重 9.8G + KV cache 8G），在 24GB 卡上可行但偏紧。

## 2. use_model 默认为 false

**现象**: 写了 `use_model: false`，跑了半天才发现实体/关系/事件都是空的——因为规则模式不输出关系和事件。

**原因**: pipeline 脚本写 extract 调用时顺手写了 false，没人意识到应该改成 true。

**教训**: 本地有模型就应该用模型。`use_model` 的默认值应该全局检查。pipeline 的 extract 步骤必须用 `use_model: true`。

## 3. Prompt 模板的 .format() 与 JSON 花括号冲突

**现象**: DeepSeek 调用的 prompt 模板用了 `{book_title}` 变量占位符，同时模板内有 JSON 示例的 `{}`。Python 的 `.format()` 把 JSON 的 `{}` 也当成了占位符，报 `KeyError`。

**修复**: 把 `prompt_template.format()` 改为 `prompt_template.replace('{book_title}', book_title)` 链式调用，避免花括号冲突。

**教训**: 含 JSON 代码的模板不要用 `.format()`，用 `.replace()` 或 `string.Template`。

## 4. Prior hint 的 chapter_patterns 格式问题

**现象**: DeepSeek 返回 `"第X回"` 这种伪正则，不是 `"第\\d+回"`。splitter 用 `re.compile()` 编译后匹配不到任何内容。

**修复**: prompt 模板中明确要求返回**可直接编译的 Python 正则**，并给出了 `第\\d+回` 的正确示例。

**教训**: 调 LLM 输出代码/正则时，prompt 必须给出精确的格式示例，不能假定模型理解"正则"含义。

## 5. 远端 shell 环境 nohup 进程被杀死

**现象**: 通过 SSH 或 bash tool 启动的 `nohup ... &` 后台进程，在 shell 会话结束后收到 SIGHUP 被杀死。

**原因**: 某些 shell 环境（如 bash tool）在命令结束后会向子进程发送 SIGHUP。

**修复**:
- 使用 `systemd-run --user --unit=xxx` 创建持久化 transient service
- 或者在本地终端（非 bash tool）直接运行 nohup

**教训**: 不在远端 shell 环境中启动需要长期运行的后台任务。优先用 systemd 管理服务。

## 6. extract 数据量对比

| 模式 | mentions | profiles | decisions | 耗时 |
|------|----------|----------|-----------|------|
| 规则模式 (use_model=false) | 1793 | 1042 | 14597 | ~6s |
| 混合模式 (use_model=true 但有 400 回退) | 213 | 20 | 226 | ~6s |

模型提取失败时回退到规则模式，但回退后的 `_rule_extract` 只取候选词前 15 个，导致 mention 数大幅减少。

**修复**: `_rule_extract` 优化使用 prior_hint 的角色名、别名、地点扩充候选列表。

## 8. 单点修复陷阱——修改一个参数必须审计整个链路

**现象**: 反复出现同一类问题——改了一个参数，但关联参数没同步调整，导致新问题。

**典型案例**:
1. 改 `use_model=true` → 但没检查 `ctx-size` 是否足够 → 模型返回 400
2. 改 `ctx-size=65536` → 但没同步加 `max_tokens` → 模型输出被截断，JSON 解析失败
3. 改 `max_tokens=16384` → 但没提 `temperature` → 输出过于保守
4. 改代码配置 → 但没检查 `.env` 是否同步 → 环境变量不生效
5. 改 `.env` → 但没重启 `systemd service` → 配置未加载

**修复模板**: 修改模型/管线相关参数时，必须执行以下检查清单：
1. 这个改动会影响哪些下游？
2. 同一链路里还有哪些参数需要联动？
3. 配置改完后需要重启哪些服务？
4. 改完后如何验证？

具体到 NovelBridge 的模型提取链路，参数联动关系为：

```
ctx-size (总上下文) ≥ input_tokens + max_tokens (输出)
input_tokens ≈ system_prompt + chunk_text + candidates + prior_hint
```

所以改 `ctx-size` 时必须同时评估 `max_tokens`，反之亦然。

**教训**: 不要在快速迭代中丢失系统视角。每次改动前先画一条完整的参数链路图。

## 9. 模型输出 JSON 格式不匹配

**现象**: `use_model=true` 跑了 84 分钟，102 章全部成功，但只产出 122 个 mention。

**根因**: 模型输出的 JSON key 是 `entities`，但管线构建 `build_chapter_fact` 读取的是 `entity_mentions`。同时模型输出的 JSON 本身有语法错误（缺逗号），`chat_json` 解析失败后回退到规则模式。

**修复**:
1. **Prompt 指定精确 JSON 格式**：不给模型自由发挥空间，明确告知字段名和结构
2. **GBNF Grammar**：用 llama.cpp 的 grammar 机制，**强制**模型只能输出合法 JSON，彻底杜绝格式错误
3. **chapter_summary**：模型输出的概要字段现在被正确传递到 `build_chapter_fact`

**教训**: LLM 输出自由文本时，JSON 格式不可靠。必须同时用：
- 精确的 prompt template（指定 key 名和嵌套结构）
- Grammar 约束（服务端强制输出合法 JSON）
- 健壮的 fallback 处理（JSON 解析失败时不能静默吞掉数据）

## 10. Facts 索引全部失败

**现象**: `chunks_indexed=102, facts_indexed=0, failed=102`

**根因**: `chapter_fact` 的 `summary` 字段传的是空字符串 `''`，embedding 客户端检查 `if not text_for_embedding: failed += 1`。

**修复**: prompt 增加了 `chapter_summary` 输出，管线读取后正确传递给 `build_chapter_fact`。

## 11. Neo4j 认证失败：.env 变量名不匹配

**现象**: Stage 8 图投影显示 `status: success, entities=480, relations=98`，但 Neo4j 查询返回空。日志显示 `Neo.ClientError.Security.Unauthorized — missing key 'credentials'`。

**根因**: `.env` 中只有 `NEO4J_AUTH=neo4j/12345678`（Docker Compose 用），但 `config.py` 读的是 `neo4j_password`（env var: `NEO4J_PASSWORD`）。两个变量名完全不匹配，`neo4j_password=""` 空字符串导致认证失败。

**修复**: `.env` 中增加 `NEO4J_PASSWORD=12345678`。

**教训**: 
- Docker Compose 的环境变量和 Python 配置的环境变量是两套命名体系，必须分别设置。
- 修复链：`main.py` 加 `configure()` 调用 → `.env` 加对应密码变量 → 重启 service → 验证 Neo4j 写入。
- 静默失败比显式错误更危险——`if not self._configured: return` 让 graph 写出 0 错误 0 告警，但数据全丢。应该至少打一条 warn 日志。

## 12. 事件抽取：model 输出 description，narrative_builder 读 summary

**现象**: event_mentions=243 但 event_facts=0 → Neo4j events=0。

**根因**: 两层 key 名不匹配：
1. GBNF grammar 和 prompt 中事件字段叫 `description`，但 `narrative_builder.py:87` 读的是 `evt.get('summary', '')`
2. `chapter_fact_builder.py` 虽然存的是 `chapter_fact.fact_json['events']`，但每个 event 对象里的字段名是 `description` 不是 `summary`
3. `narrative_builder.py:133` 的聚合条件 `if evt['event_type'] and evt['summary']:` 因为 summary 为空永远为 false

所以 event mention 能入库（insert_batch 不校验 summary 非空），但聚合为 event fact 时全被过滤掉了。

**修复方向**: `narrative_builder.py:87` 改为 `evt.get('summary', '') or evt.get('description', '')`

## 13. 规则回退导致 facts 索引失败

**现象**: `facts_indexed=30, failed=5`，5 个 ChapterFact 未能索引到 Qdrant。

**根因**: `vector_index_store.py:88-91` 检查 `text_for_embedding = f.get('summary', '') or ''`，为空时 `failed += 1`。
这 5 条 fact 的 chunk 在模型提取时超时回退到了规则模式，而规则回退的 `_rule_extract` 输出 `chapter_summary: ""`。

**修复方向**: 在 `_rule_extract` 中 fallback 时用 chunk 文本的前 100 字作为 summary。

## 14. 导出 API 返回 unknown 错误

**现象**: export/chapter-facts 和 export/qa-pairs 都返回 `ERROR: unknown`。

**根因**: `DatasetExporter` 在无数据时返回 `{'status': 'error', 'message': '...'}`（key 为 `message`）。但 pipeline 脚本 `call_api` 读取的是 `body.error`：
```bash
err_msg=$(... get('error','unknown') ...)
```
key 名不匹配导致显示 `unknown`。

**修复方向**: 改 `DatasetExporter` 的 error 返回用 `error` 字段而非 `message`，或者脚本同时兼容 `message`。

## 15. Embedding 模型编码卡死：chunk 过大 + 线程上下文错误

### 现象
- `POST /api/books/{id}/index` 调用后无返回，curl 超时
- 服务健康检查正常，但 index 请求没有任何日志输出
- 进程 CPU 占用 300-800%，持续数分钟无响应

### 根因（三层嵌套）

**第一层：chunk 过大导致 CPU 编码极慢**
Book 8（搜神记）最大 chunk 有 21584 字节（≈7000-10000 tokens）。SentenceTransformer.encode() 在 CPU 上处理这些长文本非常慢——10 条一批要几十秒甚至几分钟。

**第二层：同步阻塞 uvicon 事件循环**
`embed_batch_sync()` 是 CPU 密集型同步调用，直接在 async handler 中执行时阻塞了 uvicorn 事件循环，导致 HTTP 响应无法写回，curl 一直等待。

**第三层（已修复）：PyTorch 在工作线程初始化导致 MKL 混乱**
首次请求时 `SentenceTransformer()` 在 `run_in_executor` 的工作线程中初始化，PyTorch 的 OpenMP/MKL 线程池在非主线程初始化后行为异常，导致 CPU 线程爆炸（16 核跑满），进一步拖死系统。

### 修复方案
1. **主线程预加载模型**：`main.py` lifespan 中调用 `_load_model()`，避免 PyTorch 在工作线程初始化
2. **CPU 密集型操作卸到线程池**：整个 index 流程用 `asyncio.to_thread(self._index_book_sync)` 扔出事件循环
3. **限制 MKL 线程数**：`OMP_NUM_THREADS=4` 防止 CPU 线程爆炸
4. **动态截断（兜底）**：仅对超过 40000 字符的超长文本截断（实际 chunk 通常只有几千字，不影响）
5. **终极方案**：客户端控制 chunk 大小 ≤ 10000 字符

### 关键发现
- Qwen3-Embedding-0.6B 的 max_position_embeddings=32768 tokens
- 中文 token 比例约 1.57 chars/token → 80% 上限 ≈ 41000 字符
- **当前所有 chunk 都远低于这个上限**，之前卡死不是内容长度问题
- 真正原因是 MKL 线程爆炸 + 事件循环阻塞

### 教训
- CPU 上的 embedding 编码不是"即时的"，需要扔到线程池
- async handler 中不能直接跑 CPU 密集型同步代码
- PyTorch 初始化必须在主线程，否则 MKL 线程行为不可预测
- 先诊断再修：之前浪费了大量时间猜截断长度，实际测一下 tokenizer 比例就清楚了

## 16. systemctl restart 卡死问题

**现象**: `systemctl --user restart rag-agent.service` 经常卡在 `deactivating` 状态。

**原因**: uvicorn 的优雅关闭等待已有请求完成，如果某请求卡住（如 embedding 模型首次加载），shutdown 就等不完。

**修复**: 先 `systemctl --user kill rag-agent.service -s KILL` 强制杀，再 `reset-failed`，再 `start`。

**教训**: systemd user service 的 restart 在进程响应慢时会卡死。必须用 kill -9 强杀。

## 17. GPU 分配被遗忘：llama-server 和 embedding 都应在 cuda:1

**现象**: 
- Embedding 用 CPU 跑了 9 秒/10 条，实际有 RTX 3090 空闲
- llama-server 被误以为在 cuda:0，实际已在 cuda:1
- 代码改了 `device='cuda:1'` 但没同步删 `CUDA_VISIBLE_DEVICES=1`，导致 `invalid device ordinal`

**服务器 GPU 配置**:
- 物理 GPU 0（RTX 3090 × 24GB）：**空闲**（当前无服务使用）
- 物理 GPU 1（RTX 3090 × 24GB）：**llama-server (9B Q8_0 ~10GB) + embedding (0.6B ~1.2GB)** 共存

**所有 GPU 相关配置必须对齐的位置**：

| 位置 | 用途 | 值 |
|------|------|:---:|
| `start_remote_services.sh:147` | llama-server 启动 | `CUDA_VISIBLE_DEVICES=1` |
| `app/clients/embedding_client.py:34` | SentenceTransformer 加载 | `device="cuda:1"` |
| `rag-agent.service` | 不要加 `CUDA_VISIBLE_DEVICES=1`（否则物理 GPU1 映射为 cuda:0，代码里的 `cuda:1` 找不到） | 不设 |

**CUDA_VISIBLE_DEVICES 的副作用**：设了 `CUDA_VISIBLE_DEVICES=1` 后，物理 GPU1 在应用看来是 `cuda:0`。如果代码里写死了 `device="cuda:1"`，就会报 `invalid device ordinal`。

要么统一行为：
- 方案 A（推荐）：代码用 `device="cuda:1"`，不设 `CUDA_VISIBLE_DEVICES`
- 方案 B：代码用 `device="cuda:0"`，设 `CUDA_VISIBLE_DEVICES=1`

混用就会出问题。

**复现时浪费的时间**：
1. 在 CPU-only PyTorch（2.12.0+cpu）上 debug 了 1 小时，以为是线程池问题
2. 换到 conda 环境（有 CUDA）后没检查 `CUDA_VISIBLE_DEVICES`，又卡了 30 分钟

**教训**: 
- 多 GPU 机器的 GPU 分配策略必须写死、贴墙、让所有人都知道
- 任何时候改 GPU 配置，检查链路：启动脚本 → 应用代码 → 服务配置 → 环境变量
- 先用 `lsof /dev/nvidia*` 确认进程真的在哪个 GPU，不要猜
