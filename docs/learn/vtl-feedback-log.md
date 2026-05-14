# VTL Feedback Log

用于先记录 `vibe-learn` 的改进候选。普通开发时不要自动改 skill；等问题重复出现或用户明确要求时再迭代 skill。

| 日期 | 阶段 | 现象 | 当前 skill 没帮到的地方 | 建议改动 | 证据 | 优先级 |
|---|---|---|---|---|---|---|
| 2026-05-13 | demo-0-design-triage | 原 skill 偏阶段学习，缺少 demo-first 默认循环 | 新手不应该在 demo/learning/hardening/practice 间选择模式 | 收敛为 demo-first loop；learning/hardening/practice 作为事件 | 用户反馈“四个模式没必要” | high |
| 2026-05-13 | demo-0-design-triage | `vtl_scan.py` 误判根目录无 Maven 项目 | 脚本假设 `pom.xml` 在仓库根目录 | 支持递归服务发现和 `.vtl/vtl-adapter.json` | 后端实际在 `Novel-Bridge/pom.xml` | high |
