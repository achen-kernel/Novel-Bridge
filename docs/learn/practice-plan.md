# 练习计划

本文件记录从完整代码生成的练习副本。当前项目先做 demo，不急着生成练习；只有在某个功能完整、验证通过后，才添加 `@VTL-PRACTICE` 标记并生成快照。

当前策略：练习不是每轮强制产物。部署、规划、Prompt/GBNF、远程服务编排等阶段可以跳过练习，但必须写明 `SKIP-PRACTICE` 原因，避免 agent 为了过检查而硬找低价值代码。

## 练习版本

| 版本 | 来源阶段 | 目标 | 来源提交 | 练习分支/worktree | 状态 |
|---|---|---|---|---|---|
| demo-1-book-import | Demo 1 | 练习 Book/Chapter 导入链路 | 待定 | 待定 | planned |
| demo-2-agent-run | Demo 2 | 练习 AgentRun/AgentStep 状态流 | 待定 | 待定 | planned |
| demo-3-citation | Demo 3 | 练习 ChatMessage/Citation 引用链路 | 待定 | 待定 | planned |

## 跳过练习记录

| 阶段 | 原因 | 后续补偿 |
|---|---|---|
| demo-5a-remote-foundation | SKIP-PRACTICE：远程 Linux 部署、一键启动、端口和 health check 属于工作流/运维闭环，不适合生成 Java TODO 练习 | 在 retro/playbook 中沉淀远程部署和服务编排规则 |
| demo-5b-entity-extraction | SKIP-PRACTICE：优先跑通 GBNF、schema validate、model_run、candidate/review 闭环；等实体抽取代码稳定后再挑选高价值方法 | Demo 6 前回看 rag-agent validator 或 review service 是否适合标记 |

## 练习标记

| 版本 | 文件 | 方法/代码块 | 难度 | 标记理由 | 状态 |
|---|---|---|---|---|---|

## 生成规则

- 完整代码先在主开发分支通过验证。
- 只转换带 `@VTL-PRACTICE` 的代码。
- 生成前先运行 dry-run：

```powershell
python .opencode\skills\vibe-learn\scripts\vtl_practice.py --version <version> --source . --target ..\Novel-Bridge-practice --dry-run --json
```

- 练习副本应在单独 worktree 或 practice 分支中完成。
