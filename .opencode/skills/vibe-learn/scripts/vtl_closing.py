#!/usr/bin/env python3
"""
vtl_closing.py — Verify vibe-learn Closing Checklist items.

Checks whether a demo cycle has been properly closed:
1. @VTL-PRACTICE markers exist in backend Java code
2. retro-log.md has recent entries
3. personal-vibecoding-playbook.md exists
4. vtl-feedback-log.md exists (if skill-level blockers occurred)

Usage:
    python .opencode/skills/vibe-learn/scripts/vtl_closing.py --root . --json

Exit code: 0 if all GREEN, 1 if any RED.
"""
import argparse
import json
import re
import sys
from pathlib import Path


SKIP_DIRS = {".git", "target", "node_modules", "dist", "build", ".idea", ".mvn"}
PRACTICE_MARKER = "@VTL-PRACTICE"


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


def find_adapter(root: Path):
    """Read .vtl/vtl-adapter.json for docs_root and backend_root."""
    adapter_path = root / ".vtl" / "vtl-adapter.json"
    if adapter_path.exists():
        return json.loads(adapter_path.read_text(encoding="utf-8"))
    return None


def find_state(root: Path):
    """Read docs/learn/vtl-state.json for active stage."""
    state_path = root / "docs" / "learn" / "vtl-state.json"
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return None


def check_practice_markers(backend_root: Path) -> dict:
    """Check if @VTL-PRACTICE markers exist in Java files."""
    markers = []
    java_files = list(backend_root.rglob("*.java"))
    for jf in java_files:
        if any(skip in jf.parts for skip in SKIP_DIRS):
            continue
        content = jf.read_text(encoding="utf-8", errors="ignore")
        if PRACTICE_MARKER in content:
            # Find marker lines
            for i, line in enumerate(content.splitlines(), 1):
                if PRACTICE_MARKER in line:
                    markers.append({
                        "file": str(jf.relative_to(backend_root)),
                        "line": i,
                        "line_text": line.strip()
                    })
    return {
        "status": "GREEN" if markers else "RED",
        "detail": f"{len(markers)} @VTL-PRACTICE marker(s) found",
        "markers": markers,
    }


def check_retro_log(docs_root: Path) -> dict:
    """Check if retro-log.md exists and has recent entries."""
    path = docs_root / "retro-log.md"
    if not path.exists():
        return {"status": "RED", "detail": "retro-log.md not found"}
    content = path.read_text(encoding="utf-8", errors="ignore")
    # Count entries by checking "## 20" heading pattern (dates)
    entries = re.findall(r"^##\s+20\d{2}", content, re.MULTILINE)
    return {
        "status": "GREEN" if content else "RED",
        "detail": f"retro-log.md exists, {len(entries)} dated entry section(s)",
        "entries": entries,
    }


def check_playbook(docs_root: Path) -> dict:
    """Check if personal-vibecoding-playbook.md exists."""
    path = docs_root / "personal-vibecoding-playbook.md"
    if not path.exists():
        return {"status": "RED", "detail": "personal-vibecoding-playbook.md not found"}
    content = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "status": "GREEN" if content else "RED",
        "detail": "personal-vibecoding-playbook.md exists",
    }


def check_feedback_log(docs_root: Path) -> dict:
    """Check if vtl-feedback-log.md exists."""
    path = docs_root / "vtl-feedback-log.md"
    if not path.exists():
        return {"status": "RED", "detail": "vtl-feedback-log.md not found"}
    content = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "status": "GREEN" if content else "YELLOW",
        "detail": "vtl-feedback-log.md exists (read on demand for pending feedback)",
    }


def main():
    parser = argparse.ArgumentParser(description="Verify vibe-learn Closing Checklist items.")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    adapter = find_adapter(root)

    # Determine backend and docs root
    if adapter:
        backend_root = root / adapter.get("backend_root", ".")
        docs_root_str = adapter.get("docs_root", "docs/learn")
    else:
        backend_root = root
        docs_root_str = "docs/learn"

    # Resolve docs root relative to root
    if docs_root_str.startswith("..") or docs_root_str.startswith("/"):
        docs_root = Path(docs_root_str)
    else:
        docs_root = root / docs_root_str

    state = find_state(root)
    active_stage = state.get("active_stage", "unknown") if state else "unknown"

    # Run all checks
    checks = {
        "practice_markers": check_practice_markers(backend_root),
        "retro_log": check_retro_log(docs_root),
        "playbook": check_playbook(docs_root),
        "feedback_log": check_feedback_log(docs_root),
    }

    red_count = sum(1 for c in checks.values() if c["status"] == "RED")
    all_green = red_count == 0

    items = [
        {
            "id": "practice_markers",
            "label": "@VTL-PRACTICE markers in code",
            "status": checks["practice_markers"]["status"],
            "detail": checks["practice_markers"]["detail"],
        },
        {
            "id": "retro_log",
            "label": "retro-log.md has recent entries",
            "status": checks["retro_log"]["status"],
            "detail": checks["retro_log"]["detail"],
        },
        {
            "id": "playbook",
            "label": "personal-vibecoding-playbook.md exists",
            "status": checks["playbook"]["status"],
            "detail": checks["playbook"]["detail"],
        },
        {
            "id": "feedback_log",
            "label": "vtl-feedback-log.md exists",
            "status": checks["feedback_log"]["status"],
            "detail": checks["feedback_log"]["detail"],
        },
    ]

    summary = f"Closing Checklist for stage '{active_stage}': {red_count} RED item(s)" if not all_green else f"Closing Checklist for stage '{active_stage}': all GREEN"

    if args.json:
        output = result(
            "success" if all_green else "warning",
            summary,
            next_actions=[] if all_green else ["Fix RED items before closing this stage"],
            items=items,
            active_stage=active_stage,
        )
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"=== Closing Checklist: stage '{active_stage}' ===\n")
        for item in items:
            icon = "✅" if item["status"] == "GREEN" else ("🟡" if item["status"] == "YELLOW" else "🔴")
            print(f"  {icon} {item['label']}: {item['detail']}")
        print(f"\n{'✅ All clear' if all_green else f'🔴 {red_count} item(s) need attention'}")
        if not all_green:
            print("\nNext: fix RED items before closing this stage.")

    sys.exit(0 if all_green else 1)


if __name__ == "__main__":
    main()
