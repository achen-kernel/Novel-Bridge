# 练习计划

本文件记录从完整代码生成的练习副本。当前项目先做 demo，不急着生成练习；只有在某个功能完整、验证通过后，才添加 `@VTL-PRACTICE` 标记并生成快照。

## 练习版本

| 版本 | 来源阶段 | 目标 | 来源提交 | 练习分支/worktree | 状态 |
|---|---|---|---|---|---|
| demo-1-book-import | Demo 1 | 练习 Book/Chapter 导入链路 | 待定 | 待定 | planned |
| demo-2-agent-run | Demo 2 | 练习 AgentRun/AgentStep 状态流 | 待定 | 待定 | planned |
| demo-3-citation | Demo 3 | 练习 ChatMessage/Citation 引用链路 | 待定 | 待定 | planned |

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
