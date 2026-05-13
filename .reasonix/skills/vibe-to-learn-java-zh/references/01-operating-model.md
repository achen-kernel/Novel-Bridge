# 运行模型

本 skill 是从零开始的学习 harness，不是项目管理工具、架构课程或完整 observability 系统。

## 核心分工

- 开发 Plan：可以来自用户、基础模型或专门的 plan skill。
- 学习计划：由本 skill 根据开发 Plan 转化。
- 开发分支：`main` 或用户的正常开发分支，始终保持可运行。
- 练习分支/worktree：从 `main` 生成，只把被标记的代码转换成 TODO 练习。

## 默认循环

1. 检查 Plan 是否足够适合学习。
2. 启动一个活跃阶段。
3. 让开发 Agent 在 `main` 上实现完整功能。
4. 用脚本收集紧凑事实。
5. 只解释当前阶段需要的学习点。
6. 只在事件发生时记录链路、练习和复盘。
7. 在版本检查点生成练习快照。
8. 在重复错误、重要检查点或项目结束时更新个人工作法。

## 非目标

- v0.1 不把已有项目导览作为一等模式。
- 不提前讲大而全的软件工程理论。
- 不生成企业级 PRD。
- v0.1 不做自动评分平台。
- 不长期手工维护 practice 分支；每个阶段快照从 `main` 重新生成。

## Token 预算

默认读取：

- `docs/learn/vtl-state.json`
- `docs/learn/current-stage.md`

按需读取：

- 阶段切换时读 `learning-plan.md`。
- API、DTO/VO、数据库、Vue 字段变化时读 `flow-map.md`。
- 练习标记和快照时读 `practice-plan.md`。
- Bug、Agent 偏差、需求决策变化时读 `retro-log.md`。
- 版本检查点和最终复盘时读 `personal-vibecoding-playbook.md`。
