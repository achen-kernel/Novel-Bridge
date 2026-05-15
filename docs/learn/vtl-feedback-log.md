# VTL Feedback Log

用于先记录 `vibe-learn` 的改进候选。普通开发时不要自动改 skill；等问题重复出现或用户明确要求时再迭代 skill。

| 日期 | 阶段 | 现象 | 当前 skill 没帮到的地方 | 建议改动 | 证据 | 优先级 |
|---|---|---|---|---|---|---|
| 2026-05-13 | demo-0-design-triage | 原 skill 偏阶段学习，缺少 demo-first 默认循环 | 新手不应该在 demo/learning/hardening/practice 间选择模式 | 收敛为 demo-first loop；learning/hardening/practice 作为事件 | 用户反馈"四个模式没必要" | high |
| 2026-05-13 | demo-0-design-triage | `vtl_scan.py` 误判根目录无 Maven 项目 | 脚本假设 `pom.xml` 在仓库根目录 | 支持递归服务发现和 `.vtl/vtl-adapter.json` | 后端实际在 `Novel-Bridge/pom.xml` | high |
| 2026-05-14 | demo-2-agent-run | 验证通过后跳过 Practice/Retro | 8 步循环没挂到 orchestrator 验证流程 | SKILL.md 新增 Closing Checklist 章节 + vtl_closing.py 脚本 | retro-log 显示 Demo 1 完成后未标记 practice | high |
| 2026-05-14 | demo-2-agent-run | 项目缺少标准分层架构 | skill 只定义 demo 循环，不约束代码结构 | SKILL.md 新增 Common module conventions + project-skeleton.md | 用户反馈没有 Service 接口、无统一响应/异常 | medium |
| 2026-05-15 | demo-3-chat | JPA 不符合用户对 Mapper + SQL 映射的预期 | skill 没有规定 ORM 策略 | SKILL.md 新增 ORM convention 章节 + project-skeleton.md 写明 MyBatis 作为默认 | 用户要求从 JPA 换 MyBatis | high |
| 2026-05-15 | demo-3-chat | practice 副本在 IDEA 中无法扫描 TODO、需手动配 JDK | vtl_practice.py 不生成 IDEA 配置 | 新增 `generate_idea_config()` 生成 .idea/ 文件；SKILL.md 增加 IDE support 章节 | 用户反馈 IDEA 扫不到 TODO | medium |
| 2026-05-15 | demo-3-chat | skill 的架构约定偏 Java/Spring Boot，其他语言不好复用 | SKILL.md 的 Common module conventions 未标注技术栈范围 | 在 conventions 和 IDE support 章节添加 Technology note 说明适用范围 | 用户主动提出"能不能更通用" | medium |
