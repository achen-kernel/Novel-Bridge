#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


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


def templates():
    return {
        "learning-plan.md": (
            "# Learning Plan\n\n"
            "## Demo-First Track\n\n"
            "| Version | Demo slice | Feature goal | Learning goal | Acceptance evidence | Status |\n"
            "|---|---|---|---|---|---|\n\n"
            "## Hardening Track\n\n"
            "| Version | Hardening item | Goal | Acceptance evidence | Status |\n"
            "|---|---|---|---|---|\n\n"
            "## Version Checkpoints\n\n"
            "Prompt the user to inspect this file at core module completion or version iteration points.\n"
        ),
        "current-stage.md": (
            "# Current Stage\n\n"
            "- Stage id:\n"
            "- Version:\n"
            "- Status: planned\n"
            "- Loop: demo-first\n"
            "- Demo slice:\n"
            "- Feature goal:\n"
            "- Not in scope:\n"
            "- Mock/temporary work:\n"
            "- Likely files:\n"
            "- Learning goals:\n"
            "- Acceptance evidence:\n"
            "- Backend/full-stack checkpoints:\n"
            "- Practice candidates:\n"
            "- Open risks:\n\n"
            "## Agent Contract\n\n"
            "- Build:\n"
            "- Do not build:\n"
            "- Verify:\n"
            "- Update docs when:\n"
        ),
        "demo-plan.md": (
            "# Demo Plan\n\n"
            "## Walking Skeleton\n\n"
            "| Round | Visible user path | Real implementation | Mock/debt | Evidence | Status |\n"
            "|---|---|---|---|---|---|\n\n"
            "## Debt List\n\n"
            "| Source round | Debt | Why allowed | When to harden | Status |\n"
            "|---|---|---|---|---|\n"
        ),
        "flow-map.md": (
            "# Flow Map\n\n"
            "## Backend Flow\n\n"
            "| Feature | Controller | Service | Mapper/Repository | DB table | Notes |\n"
            "|---|---|---|---|---|---|\n\n"
            "## API Contracts\n\n"
            "| Feature | Method | Path | Request | Response | Frontend caller |\n"
            "|---|---|---|---|---|---|\n\n"
            "## Full-Stack Field Trace\n\n"
            "| Page field | Vue state | API param | DTO field | Service handling | DB column | VO field | Rendered output |\n"
            "|---|---|---|---|---|---|---|---|\n"
        ),
        "practice-plan.md": (
            "# Practice Plan\n\n"
            "## Versions\n\n"
            "| Version | Stage | Goal | Status | Source commit |\n"
            "|---|---|---|---|---|\n\n"
            "## Practice Markers\n\n"
            "| Version | File | Name | Level | Rationale | Status |\n"
            "|---|---|---|---|---|---|\n"
        ),
        "retro-log.md": (
            "# Retro Log\n\n"
            "## Bugs\n\n"
            "| Date | Stage | Symptom | Cause | Fix | Learning point |\n"
            "|---|---|---|---|---|---|\n\n"
            "## Agent Drift\n\n"
            "| Date | Stage | Drift | Impact | Future rule |\n"
            "|---|---|---|---|---|\n\n"
            "## Decisions\n\n"
            "| Date | Stage | Decision | Reason | Effect |\n"
            "|---|---|---|---|---|\n"
        ),
        "personal-vibecoding-playbook.md": (
            "# Personal Vibe Coding Playbook\n\n"
            "## My Stage Workflow\n\n"
            "1. Confirm the stage goal and not-in-scope items.\n"
            "2. Ask the agent which files it expects to touch.\n"
            "3. Require verification before accepting completion.\n"
            "4. Record flow and learning points.\n"
            "5. Mark practice candidates only after the complete solution works.\n\n"
            "## My Agent Prompt Rules\n\n"
            "| Rule | Evidence | Confidence | Applies when |\n"
            "|---|---|---|---|\n\n"
            "## My Weak Spots\n\n"
            "| Topic | Evidence | Next practice |\n"
            "|---|---|---|\n"
        ),
        "vtl-feedback-log.md": (
            "# VTL Feedback Log\n\n"
            "Use this to log skill improvement candidates first. Do not auto-edit the skill during ordinary development.\n\n"
            "| Date | Stage | Symptom | What the skill missed | Suggested change | Evidence | Priority |\n"
            "|---|---|---|---|---|---|---|\n"
        ),
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

    state = {
        "schema": "vtl-state-v0.2",
        "project_mode": "build_from_zero",
        "loop": "demo-first",
        "learner_goal": args.goal,
        "main_branch": args.main_branch,
        "practice_branch": args.practice_branch,
        "active_stage": None,
        "stage_status": None,
        "backend_root": None,
        "frontend_root": None,
        "rag_root": None,
        "cost_mode": args.cost,
        "doc_policy": "compact_event_driven",
        "skill_feedback_policy": "log_first_edit_on_request",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_if_needed(learn / "vtl-state.json", json.dumps(state, indent=2, ensure_ascii=False) + "\n", args.force, created, skipped)
    for name, content in templates().items():
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
