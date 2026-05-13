#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path


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
    state = read_json(state_path)
    warnings = []
    if state is None:
        warnings.append("Missing or invalid docs/learn/vtl-state.json.")
    if not stage_path.exists():
        warnings.append("Missing docs/learn/current-stage.md.")

    branch = git(["branch", "--show-current"], root)
    dirty = git(["status", "--porcelain"], root)
    next_actions = []
    if state is None:
        next_actions.append("Run scripts/vtl_init.py --json")
    else:
        if not state.get("active_stage"):
            next_actions.append("Create the first active stage in current-stage.md")
        else:
            next_actions.append("Continue the active stage and use vtl_changes.py before broad file reads")

    output = result(
        "success" if not warnings else "warning",
        "Loaded VTL status.",
        recommended_reads=[str(stage_path)] if stage_path.exists() else [],
        next_actions=next_actions,
        warnings=warnings,
        state=state,
        current_branch=branch,
        git_dirty=bool(dirty),
        current_stage_preview=first_lines(stage_path),
    )
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output["summary"])


if __name__ == "__main__":
    main()
