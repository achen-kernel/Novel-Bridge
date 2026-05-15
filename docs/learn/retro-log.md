# retro-log.md

## 2026-05-14 — Architecture hardening (Post-Demo 2)

### 新增：统一响应模型 + 异常体系
- **新增**：`common/result/Result<T>` 统一 API 响应（code=1/0, msg, data）
- **新增**：`common/exception/BaseException` 业务异常基类
- **新增**：`common/handler/GlobalExceptionHandler` 全局异常处理器
- **新增**：`common/properties/BooksProperties` — `@ConfigurationProperties` 替代 `@Value` 硬编码
- **改造**：BookController 从 `ResponseEntity<VO>` 改为 `Result<VO>`
- **改造**：BookServiceImpl 从 `@Value` 注入改为 `BooksProperties` 注入
- **改造**：NovelBridgeApplication 增加 `@ConfigurationPropertiesScan`
- **学习点**：@Value 适合简单取值，@ConfigurationProperties 适合配置集中管理、类型安全、IDE 自动补全
- **学习点**：RestControllerAdvice 的异常处理优先级：子类优先。BaseException → IllegalArgumentException → MethodArgumentNotValidException → Exception

## 2026-05-14 — Demo 1 ~ 2

### Bug: PowerShell curl 导致 JSON 解析失败
- **现象**：`JSON parse error: Unexpected character ('f'...)`，POST 请求体被截断
- **根因**：PowerShell 的 `curl` 别名在反引号换行时损坏了 JSON
- **修复**：改用 `Invoke-RestMethod` 或 Apifox
- **教训**：shell 的 curl 实现在不同平台行为不同，怀疑时先试 `Invoke-RestMethod`

### 决策：application.properties → application.yml
- **原因**：单文件不够分层，不便区分 dev/prod 配置
- **方案**：拆为 `application.yml`（公共）+ `application-dev.yml`（开发环境）
- **额外**：顺便禁用了 Redis 自动连接（当前阶段不需要）

### 决策：.reasonix 废弃，迁移到 .opencode
- **原因**：项目从 Reasonix agent 切换到 OpenCode agent，两套 skill 副本不一致
- **方案**：AGENTS.md、adapter、state 所有路径改为 `.opencode/skills/vibe-learn`
- **影响**：`.reasonix/` 已加入 gitignore，不再追踪

### 决策：删除 Novel-Bridge/ 内层的冗余文件
- **删除**：`mvnw`、`mvnw.cmd`、`.mvn/`、内层 `.gitignore`、`.gitattributes`
- **原因**：使用本地 Maven，wrapper 文件和冗余配置多余
- **教训**：Spring Initializr 生成的模板文件不是都需要保留

### Agent 偏差：Demo 1 完成后跳过 Retro/Practice/Skill
- **现象**：完成了代码、验证了 DB，但忘记标记 `@VTL-PRACTICE`、忘记写 retro、忘记更新 playbook
- **根因**：orchestrator 的"执行→验证"循环和 vibe-learn 的 8 步循环没有挂钩点
- **修正**：在 AGENTS.md 补充 "vibe-learn 收尾检查清单"

## 2026-05-13 — 项目重启

### 决策：从按功能分包改为三层包结构
- **背景**：第一版代码按功能分包（user/、book/、agent/…），共 57 个文件
- **问题**：作为学习项目，按功能分包看不到每层的职责边界，不适合初学者
- **决策**：清空旧代码，改为 common / controller / pojo / server 三层结构
- **影响**：旧 57 文件已删除，从空白骨架重新开始，分 9 轮渐进实现
- **教训**：学习项目一开始就应该用清晰的分层结构

### 决策：Git 仓库位置
- **第一版**：git 建在 Novel-Bridge/ 子目录内，data/ 和 docs/learn/ 在外
- **纠正**：删掉子目录 git，在项目根目录 D:\Novel-Bridge 重新 init
- **原因**：根目录涵盖了后端、数据、文档、skill 所有内容

## 2026-05-12 — 第一次尝试

### Bug: MySQL Connector/J 9.x 不支持 utf8mb4 编码名
- **现象**：`Unsupported character encoding 'utf8mb4'`
- **修复**：JDBC URL 中 `characterEncoding=utf8mb4` → `characterEncoding=UTF-8`
- **教训**：新 JDBC 驱动对字符集编码名更严格

### 决策：EntityProfile + significance
- **原因**：区分主角与次要角色，为 v2 聚合铺路
- **字段**：significance 枚举 MAJOR / SUPPORTING / MINOR / CAMEO
- **范围**：v1 只建表 + CRUD，不做跨章聚合

### 决策：单一数据库 novel_bridge + book_id 归属
- **原因**：连接管理简单、支持后续多书问答、建表脚本可复用
