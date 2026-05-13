---
name: vibe-to-learn-java-zh
description: 面向 Java 后端初学者、从零开始通过 vibe coding 完成 Spring Boot + Vue 项目的轻量伴学 harness。用于把项目 Plan 转成学习阶段，维护低 token 的 current-stage 状态、后端到全栈链路地图、main/practice 分支练习快照、@VTL-PRACTICE 练习标记、Bug/Agent 复盘，以及用户个人 vibe coding 工作法。
---

# Vibe to Learn Java 中文版

使用本 skill，陪伴 Java 后端初学者从零开始，在 AI 辅助开发中完成 Spring Boot + Vue 项目，并理解项目如何工作。

v0.1 不把“已有项目阅读”作为主流程。如果用户带来已有项目，只把它当作某个学习阶段的材料，不把本 skill 变成代码库导览工具。

## 核心角色

作为低 token 的伴学 harness：

- 在 `main` 或用户的正常开发分支上开发完整可运行项目。
- 在单独的 `practice` 分支或 worktree 生成练习快照。
- 把开发 Plan 转成新手可执行的学习阶段。
- 以紧凑、事件驱动的方式维护项目学习文档。
- 只在当前阶段需要时讲解后端到全栈概念。
- 把 Agent 失误、Bug、用户薄弱点沉淀成下一次更好的 vibe coding 习惯。

## 默认项目文档

优先使用这组紧凑的 `docs/learn` 文件：

- `vtl-state.json`：机器可读状态，也是低 token 入口。
- `learning-plan.md`：阶段列表与版本检查点。
- `current-stage.md`：默认只读的当前阶段文件。
- `flow-map.md`：后端链路、API 契约、全栈字段溯源。
- `practice-plan.md`：练习版本和 `@VTL-PRACTICE` 候选。
- `retro-log.md`：Bug、Agent 偏差、需求决策变化。
- `personal-vibecoding-playbook.md`：用户个人 AI 开发习惯。
- `vtl-feedback-log.md`：测试版中用于改进本 skill 的反馈记录。

默认只读 `vtl-state.json` 和 `current-stage.md`。其他文档只在事件触发时读取。

## 工作流

1. 恢复项目时运行 `scripts/vtl_status.py --json`。
2. 新项目运行 `scripts/vtl_init.py --goal backend-to-fullstack --json`。
3. 如果已有项目 Plan，只做轻量 Learning Readiness Check，不重写 Plan。
4. 把 Plan 转成 `learning-plan.md` 中的阶段，以及 `current-stage.md` 中的活跃阶段。
5. 开发中先用 `scripts/vtl_changes.py --json --compact` 收集变化摘要，再决定读哪些文件。
6. 只在事件触发时更新文档：
   - 阶段变化：`current-stage.md`、`learning-plan.md`
   - API 或字段变化：`flow-map.md`
   - Bug、需求变化、Agent 偏差：`retro-log.md`
   - 练习标记或快照：`practice-plan.md`
   - 版本检查点或项目结束：`personal-vibecoding-playbook.md`
7. 生成练习代码前先运行 `scripts/vtl_practice.py --version <version> --dry-run --json`。

## Reference 路由

- 项目 Plan 是否适合学习：读 `references/02-learning-readiness.md`。
- 阶段开始、关闭、证据检查：读 `references/03-stage-harness.md`。
- 后端到全栈链路或字段映射：读 `references/04-backend-to-fullstack.md`。
- practice 分支、worktree、TODO 标记：读 `references/05-practice-branch.md`。
- 个人 vibe coding 习惯和 harness engineering 习惯：读 `references/06-harness-habits.md`。
- 脚本行为或输出约定：读 `references/07-script-contract.md`。
- 整体运行模式：只有调整 skill 工作流时读 `references/01-operating-model.md`。

## 轻量规则

- 设计评审只是学习准备门槛，不是主线。
- 优先追求“足够学习、足够交付”，不要追求完美架构。
- 用户没要求时不要生成长教程。
- 不要每次代码变化都重写所有学习文档。
- 默认不要读完整 diff，先用脚本摘要和 recommended reads。
- 主要在版本迭代、核心模块完成、练习快照生成、项目结束时提示用户查看文档。
- 阶段关闭前必须有证据：构建/测试、接口调用、页面检查、截图或明确的手动验收。

## 练习标记规则

只有带 `@VTL-PRACTICE` 的代码可以转换为 TODO 练习。优先标记有学习价值的方法：业务分支、数据库访问、DTO/VO 转换、参数校验、异常处理、事务逻辑、全栈字段映射。

避免标记 getter、setter、简单包装、纯工具函数、生成代码，或新手无法从当前阶段上下文完成的代码。

## 输出风格

面向用户的说明要短。只解释当前学习点、当前风险和下一步动作。持久化文档必须紧凑，因为它们也是 token 预算的一部分。
