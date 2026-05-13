#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def skill_language() -> str:
    path = str(Path(__file__).resolve()).lower()
    return "zh" if "vibe-to-learn-java-zh" in path else "en"


def result(status, summary, artifacts=None, recommended_reads=None, next_actions=None, warnings=None, stop_condition=None):
    return {
        "status": status,
        "summary": summary,
        "artifacts": artifacts or [],
        "recommended_reads": recommended_reads or [],
        "next_actions": next_actions or [],
        "warnings": warnings or [],
        "stop_condition": stop_condition,
    }


def write_if_needed(path: Path, content: str, force: bool, created: list, skipped: list):
    if path.exists() and not force:
        skipped.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(str(path))


def templates(lang: str):
    if lang == "zh":
        return {
            "learning-plan.md": "# 学习计划\n\n## 阶段\n\n| 版本 | 阶段 | 功能目标 | 学习目标 | 验收方式 | 状态 |\n|---|---|---|---|---|---|\n\n## 版本检查点\n\n在核心模块完成或版本迭代时，再提示用户查看本文件。\n",
            "current-stage.md": "# 当前阶段\n\n- 阶段 id:\n- 版本:\n- 状态: planned\n- 功能目标:\n- 不做事项:\n- 可能修改文件:\n- 学习目标:\n- 验收证据:\n- 后端/全栈检查点:\n- 练习候选:\n- 风险:\n\n## Agent 契约\n\n- 本阶段做:\n- 本阶段不做:\n- 必须验证:\n- 何时更新文档:\n",
            "flow-map.md": "# 链路地图\n\n## 后端链路\n\n| 功能 | Controller | Service | Mapper/Repository | 数据表 | 说明 |\n|---|---|---|---|---|---|\n\n## API 契约\n\n| 功能 | 方法 | 路径 | 请求 | 响应 | 前端调用 |\n|---|---|---|---|---|---|\n\n## 全栈字段溯源\n\n| 页面字段 | Vue 状态 | API 参数 | DTO 字段 | Service 处理 | DB 字段 | VO 字段 | 页面展示 |\n|---|---|---|---|---|---|---|---|\n",
            "practice-plan.md": "# 练习计划\n\n## 版本\n\n| 版本 | 阶段 | 目标 | 状态 | 来源提交 |\n|---|---|---|---|---|\n\n## 练习标记\n\n| 版本 | 文件 | 名称 | 难度 | 标记理由 | 状态 |\n|---|---|---|---|---|---|\n",
            "retro-log.md": "# 复盘记录\n\n## Bug\n\n| 日期 | 阶段 | 现象 | 原因 | 修复 | 学习点 |\n|---|---|---|---|---|---|\n\n## Agent 偏差\n\n| 日期 | 阶段 | 偏差 | 影响 | 下次规则 |\n|---|---|---|---|---|\n\n## 决策变化\n\n| 日期 | 阶段 | 决策 | 原因 | 影响 |\n|---|---|---|---|---|\n",
            "personal-vibecoding-playbook.md": "# 个人 Vibe Coding 工作法\n\n## 我的阶段流程\n\n1. 先确认阶段目标和不做事项。\n2. 让 Agent 说明预计修改哪些文件。\n3. 接受完成前要求验证证据。\n4. 记录链路和学习点。\n5. 完整代码能运行后再标记练习候选。\n\n## 我的 Agent 提示规则\n\n| 规则 | 证据 | 置信度 | 适用场景 |\n|---|---|---|---|\n\n## 我的薄弱点\n\n| 主题 | 证据 | 下一步练习 |\n|---|---|---|\n",
            "vtl-feedback-log.md": "# VTL Feedback Log\n\nUse this during test projects to improve the skill.\n\n| Date | Stage | What helped | What felt heavy | Script issue | Next improvement |\n|---|---|---|---|---|---|\n",
        }
    return {
        "learning-plan.md": "# Learning Plan\n\n## Stages\n\n| Version | Stage | Feature goal | Learning goal | Acceptance evidence | Status |\n|---|---|---|---|---|---|\n\n## Version Checkpoints\n\nPrompt the user to inspect this file at core module completion or version iteration points.\n",
        "current-stage.md": "# Current Stage\n\n- Stage id:\n- Version:\n- Status: planned\n- Feature goal:\n- Not in scope:\n- Likely files:\n- Learning goals:\n- Acceptance evidence:\n- Backend/full-stack checkpoints:\n- Practice candidates:\n- Open risks:\n\n## Agent Contract\n\n- Build:\n- Do not build:\n- Verify:\n- Update docs when:\n",
        "flow-map.md": "# Flow Map\n\n## Backend Flow\n\n| Feature | Controller | Service | Mapper/Repository | DB table | Notes |\n|---|---|---|---|---|---|\n\n## API Contracts\n\n| Feature | Method | Path | Request | Response | Frontend caller |\n|---|---|---|---|---|---|\n\n## Full-Stack Field Trace\n\n| Page field | Vue state | API param | DTO field | Service handling | DB column | VO field | Rendered output |\n|---|---|---|---|---|---|---|---|\n",
        "practice-plan.md": "# Practice Plan\n\n## Versions\n\n| Version | Stage | Goal | Status | Source commit |\n|---|---|---|---|---|\n\n## Practice Markers\n\n| Version | File | Name | Level | Rationale | Status |\n|---|---|---|---|---|---|\n",
        "retro-log.md": "# Retro Log\n\n## Bugs\n\n| Date | Stage | Symptom | Cause | Fix | Learning point |\n|---|---|---|---|---|---|\n\n## Agent Drift\n\n| Date | Stage | Drift | Impact | Future rule |\n|---|---|---|---|---|\n\n## Decisions\n\n| Date | Stage | Decision | Reason | Effect |\n|---|---|---|---|---|\n",
        "personal-vibecoding-playbook.md": "# Personal Vibe Coding Playbook\n\n## My Stage Workflow\n\n1. Confirm the stage goal and not-in-scope items.\n2. Ask the agent which files it expects to touch.\n3. Require verification before accepting completion.\n4. Record flow and learning points.\n5. Mark practice candidates only after the complete solution works.\n\n## My Agent Prompt Rules\n\n| Rule | Evidence | Confidence | Applies when |\n|---|---|---|---|\n\n## My Weak Spots\n\n| Topic | Evidence | Next practice |\n|---|---|---|\n",
        "vtl-feedback-log.md": "# VTL Feedback Log\n\nUse this during test projects to improve the skill.\n\n| Date | Stage | What helped | What felt heavy | Script issue | Next improvement |\n|---|---|---|---|---|---|\n",
    }


def main():
    parser = argparse.ArgumentParser(description="Initialize lightweight VTL learning docs.")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--goal", default="backend-to-fullstack")
    parser.add_argument("--main-branch", default="main")
    parser.add_argument("--practice-branch", default="practice")
    parser.add_argument("--cost", default="low")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    learn = root / "docs" / "learn"
    created, skipped = [], []
    lang = skill_language()

    state = {
        "schema": "vtl-state-v0.1",
        "project_mode": "build_from_zero",
        "learner_goal": args.goal,
        "main_branch": args.main_branch,
        "practice_branch": args.practice_branch,
        "active_stage": None,
        "stage_status": None,
        "cost_mode": args.cost,
        "doc_policy": "compact_event_driven",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_if_needed(learn / "vtl-state.json", json.dumps(state, indent=2, ensure_ascii=False) + "\n", args.force, created, skipped)
    for name, content in templates(lang).items():
        write_if_needed(learn / name, content, args.force, created, skipped)

    output = result(
        "success",
        f"Initialized VTL docs in {learn}",
        artifacts=created,
        recommended_reads=[str(learn / "vtl-state.json"), str(learn / "current-stage.md")],
        next_actions=["Review the project plan with Learning Readiness Check", "Create the first active stage"],
        warnings=[f"Skipped existing file: {p}" for p in skipped],
    )
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output["summary"])


if __name__ == "__main__":
    main()
