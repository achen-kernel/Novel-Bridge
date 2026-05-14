#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path


ADAPTER_PATH = ".vtl/vtl-adapter.json"


def result(status, summary, artifacts=None, recommended_reads=None, next_actions=None, warnings=None, stop_condition=None, **extra):
    data = {
        "status": status,
        "summary": summary,
        "artifacts": artifacts or [],
        "recommended_reads": recommended_reads or [],
        "next_actions": next_actions or [],
        "warnings": warnings or [],
        "stop_condition": stop_condition,
    }
    data.update(extra)
    return data


def git(cmd, root: Path):
    proc = subprocess.run(["git"] + cmd, cwd=root, text=True, capture_output=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def suggested_state():
    return {
        "schema": "vtl-state-v0.2",
        "loop": "demo-first",
        "active_stage": None,
        "stage_status": None,
        "backend_root": None,
        "frontend_root": None,
        "rag_root": None,
        "doc_policy": "compact_event_driven",
        "skill_feedback_policy": "log_first_edit_on_request",
    }


def first_lines(path: Path, limit=80):
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()[:limit]


def main():
    parser = argparse.ArgumentParser(description="Token-light VTL project status.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    learn = root / "docs" / "learn"
    state_path = learn / "vtl-state.json"
    stage_path = learn / "current-stage.md"
    adapter_path = root / ADAPTER_PATH
    state = read_json(state_path)
    adapter = read_json(adapter_path)
    warnings = []
    stop_condition = None
    if state is None:
        warnings.append("Missing or invalid docs/learn/vtl-state.json.")
        stop_condition = "create_vtl_state"
    if not stage_path.exists():
        warnings.append("Missing docs/learn/current-stage.md.")
        stop_condition = stop_condition or "create_current_stage"
    if not adapter_path.exists():
        warnings.append(f"Missing {ADAPTER_PATH}; optional, but recommended for multi-service projects.")

    branch = git(["branch", "--show-current"], root)
    dirty = git(["status", "--porcelain"], root)
    next_actions = []
    if state is None:
        next_actions.append("Create docs/learn/vtl-state.json or run scripts/vtl_init.py --json")
    else:
        if not state.get("active_stage"):
            next_actions.append("Create the first active stage in current-stage.md")
        else:
            next_actions.append("Continue the active stage and use vtl_changes.py before broad file reads")
    if not adapter_path.exists():
        next_actions.append(f"Run vtl_scan.py and create {ADAPTER_PATH} if service roots are not obvious")

    output = result(
        "success" if not warnings else "warning",
        "Loaded VTL status.",
        recommended_reads=[str(path) for path in [state_path, stage_path, adapter_path] if path.exists()],
        next_actions=next_actions,
        warnings=warnings,
        stop_condition=stop_condition,
        state=state,
        suggested_state=suggested_state() if state is None else None,
        adapter=adapter,
        current_branch=branch,
        git_dirty=bool(dirty),
        current_stage_preview=first_lines(stage_path),
    )
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output["summary"])


if __name__ == "__main__":
    main()
