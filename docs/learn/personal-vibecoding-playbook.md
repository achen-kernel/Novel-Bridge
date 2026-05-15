# 个人 Vibe Coding 工作法

本文件沉淀你在使用 AI coding agent 时形成的个人规则。只记录有证据、能复用的经验，不写长教程。

## 当前阶段流程

1. 先做一个小型可运行 demo。
2. 明确本轮不做什么。
3. 要求 agent 说明可能修改哪些文件。
4. 完成前必须提供构建、测试、接口、页面或手工验证证据。
5. 完整代码能运行后，再考虑 `@VTL-PRACTICE` 练习标记。
6. 出现 Bug 或 Agent 偏差时，记录成下次提示规则。
7. **【新增】每轮 demo 完成后，要求 agent 逐一核对 vibe-learn 8 步循环：status → structure → readiness → demo → evidence → harden → practice → retro。缺哪步补哪步。**

## 我的 Agent 提示规则

| 规则 | 证据 | 置信度 | 适用场景 |
|---|---|---|---|
| 先 demo 再扩展，不要一开始铺满 20 张表 | demo-0 阶段收口时发现文档规划重于可运行反馈 | high | 新项目、复杂功能、AI/RAG 项目 |
| 项目结构不符合脚本默认假设时，先写 adapter，不强行改项目结构 | 后端位于 `Novel-Bridge/` 子目录，早期 `vtl_scan.py` 误判 | high | 多服务仓库、嵌套后端项目 |
| **每轮完成后要求 agent 做代码注释审查** | Demo 1/2 结束后发现实体类没有注释、算法没有解释 | high | 任何 agent 生成的代码 |
| **每个 demo 完成后要求 agent 列出未执行的 skill 步骤** | Demo 1 完成后 retro/practice/skill 全部跳过，未被追踪 | high | 使用 vibe-learn skill 的所有对话 |
| **App 启动后先用 ApiFox 或 Invoke-RestMethod 验证，避免 shell curl 踩坑** | PowerShell curl 导致 JSON 解析失败，浪费定位时间 | medium | Windows PowerShell 环境 |

## 我的薄弱点

| 主题 | 证据 | 下一步练习 |
|---|---|---|
| 从大设计收敛到小 demo | 表设计和计划较完整，但代码仍是骨架 | Demo 1 只实现 Book/Chapter 导入 |
| Harness 工程落地 | 理解概念后还需要在代码中实现 AgentRun/AgentStep/Citation | Demo 2/3 专门练状态与引用链路 |
| **督促 agent 走完完整循环** | 两次 demo 结束后都漏了 retro/practice，需要用户手动提醒 | 加入提示规则，形成习惯 |

## Skill 改进候选

真正要修改 skill 时，先在 `vtl-feedback-log.md` 记录证据，再集中迭代。
