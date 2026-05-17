#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path


SKIP = {".git", "target", "node_modules", "dist", "build", ".idea", ".gradle"}
JAVA_MAPPING = re.compile(r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*(?:\(\s*)?(?:value\s*=\s*)?[\"']([^\"']+)[\"']")
FIELD_DECL = re.compile(r"\b(private|public|protected)\s+[\w<>, ?]+\s+(\w+)\s*(?:=|;)")
MARKER = "@VTL-PRACTICE"


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


def git_files(root: Path, since: str | None):
    repo = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, text=True, capture_output=True)
    if repo.returncode != 0:
        return [], ["Not a git repository; no change summary available."]
    commands = []
    if since:
        commands.append(["git", "diff", "--name-only", since])
    else:
        commands.extend([["git", "diff", "--name-only"], ["git", "diff", "--name-only", "--cached"]])
    files = set()
    warnings = []
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True)
        if proc.returncode != 0:
            warnings.append(proc.stderr.strip() or f"git command failed: {' '.join(cmd)}")
            continue
        for line in proc.stdout.splitlines():
            if line.strip():
                files.add(line.strip().replace("\\", "/"))
    return sorted(files), warnings


def safe_read(path: Path, max_bytes=200_000):
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def classify(path: str):
    lower = path.lower()
    if lower.endswith(".java"):
        if "/controller/" in lower:
            return "controller"
        if "/service/" in lower:
            return "service"
        if "/mapper/" in lower or "/repository/" in lower:
            return "persistence"
        if "/dto/" in lower:
            return "dto"
        if "/vo/" in lower:
            return "vo"
        if "/entity/" in lower:
            return "entity"
        return "java"
    if lower.endswith((".vue", ".ts", ".js")):
        if "/api/" in lower:
            return "frontend_api"
        return "frontend"
    return "other"


def main():
    parser = argparse.ArgumentParser(description="Emit compact change facts instead of long diffs.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--since")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files, warnings = git_files(root, args.since)
    changed = [f for f in files if not any(part in SKIP for part in Path(f).parts)]
    endpoints, fields, markers = [], [], []
    recommended = []

    for rel in changed:
        kind = classify(rel)
        if kind != "other" and len(recommended) < 12:
            recommended.append(rel)
        text = safe_read(root / rel)
        if text is None:
            continue
        if kind == "controller":
            for match in JAVA_MAPPING.finditer(text):
                endpoints.append({"file": rel, "method": match.group(1), "path": match.group(2)})
        if kind in {"dto", "vo", "entity"}:
            for match in FIELD_DECL.finditer(text):
                fields.append({"file": rel, "field": match.group(2)})
        if MARKER in text:
            for line in text.splitlines():
                if MARKER in line:
                    markers.append({"file": rel, "marker": line.strip()})

    output = result(
        "success" if not warnings else "warning",
        f"Found {len(changed)} changed files.",
        recommended_reads=recommended,
        next_actions=["Read only recommended files before updating learning docs"],
        warnings=warnings,
        changed_files=changed,
        file_kinds={rel: classify(rel) for rel in changed},
        suspected_endpoint_changes=endpoints,
        suspected_field_changes=fields[:50],
        practice_markers=markers,
    )
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output["summary"])


if __name__ == "__main__":
    main()
