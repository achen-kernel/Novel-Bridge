#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


MARKER = "@VTL-PRACTICE"
SKIP = {".git", "target", "node_modules", "dist", "build", ".idea", ".gradle"}


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


def git_clean(path: Path):
    if not (path / ".git").exists():
        return True, "not a git repo"
    proc = subprocess.run(["git", "status", "--porcelain"], cwd=path, text=True, capture_output=True)
    if proc.returncode != 0:
        return False, proc.stderr.strip() or "git status failed"
    return proc.stdout.strip() == "", proc.stdout.strip()


def source_commit(path: Path):
    proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=path, text=True, capture_output=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def should_skip(path: Path):
    return any(part in SKIP for part in path.parts)


def copy_tree(source: Path, target: Path, dry_run: bool):
    copied = []
    for src in source.rglob("*"):
        rel = src.relative_to(source)
        if should_skip(rel):
            continue
        dst = target / rel
        if src.is_dir():
            if not dry_run:
                dst.mkdir(parents=True, exist_ok=True)
            continue
        copied.append(str(rel))
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return copied


def parse_marker(lines, index):
    meta = {}
    j = index
    while j < len(lines) and lines[j].strip().startswith("//"):
        line = lines[j].strip()[2:].strip()
        if line.startswith(MARKER):
            for part in line.replace(MARKER, "").split():
                if "=" in part:
                    key, value = part.split("=", 1)
                    meta[key.strip()] = value.strip()
        elif "=" in line:
            key, value = line.split("=", 1)
            meta[key.strip()] = value.strip()
        j += 1
    return meta, j


def find_body(lines, start):
    open_line = None
    for i in range(start, len(lines)):
        if "{" in lines[i]:
            open_line = i
            break
    if open_line is None:
        return None
    depth = 0
    for i in range(open_line, len(lines)):
        depth += lines[i].count("{")
        depth -= lines[i].count("}")
        if depth == 0:
            return open_line, i
    return None


def replacement(open_line_text, meta):
    indent = re.match(r"^(\s*)", open_line_text).group(1)
    before = open_line_text.split("{")[0] + "{\n"
    goal = meta.get("goal", "complete this method")
    prereq = meta.get("prerequisites", "read the current stage, tests, and call flow")
    inputs = meta.get("inputs", "method parameters")
    outputs = meta.get("outputs", "method return value")
    pitfalls = meta.get("pitfalls", "nulls, validation, exceptions, and field mapping")
    hints = meta.get("hints", "follow the caller flow first, then fill the core logic")
    return [
        before,
        f"{indent}    // TODO: Practice goal: {goal}\n",
        f"{indent}    // Prerequisites: {prereq}\n",
        f"{indent}    // Inputs: {inputs}\n",
        f"{indent}    // Outputs: {outputs}\n",
        f"{indent}    // Watch out: {pitfalls}\n",
        f"{indent}    // Hint: {hints}\n",
        f"{indent}    throw new UnsupportedOperationException(\"TODO: complete this practice\");\n",
        f"{indent}}}\n",
    ]


def transform_file(path: Path, version: str, dry_run: bool):
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
    out, changed, planned, warnings = [], False, [], []
    i = 0
    while i < len(lines):
        if MARKER in lines[i]:
            meta, method_start = parse_marker(lines, i)
            body = find_body(lines, method_start)
            if meta.get("version") == version and body:
                open_line, close_line = body
                signature = meta.get("signature")
                if signature and signature.split("(")[0].split()[-1] not in lines[open_line]:
                    warnings.append(f"Signature may not match in {path}: {signature}")
                out.extend(lines[i:open_line])
                out.extend(replacement(lines[open_line], meta))
                planned.append({"file": str(path), "name": meta.get("name"), "version": version})
                i = close_line + 1
                changed = True
                continue
        out.append(lines[i])
        i += 1
    if changed and not dry_run:
        path.write_text("".join(out), encoding="utf-8")
    return planned, warnings


def transform_markers(target: Path, version: str, dry_run: bool):
    planned, warnings = [], []
    for path in target.rglob("*.java"):
        if should_skip(path.relative_to(target)):
            continue
        file_planned, file_warnings = transform_file(path, version, dry_run)
        planned.extend(file_planned)
        warnings.extend(file_warnings)
    return planned, warnings


def main():
    parser = argparse.ArgumentParser(description="Create a practice snapshot from marked Java methods.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--source", default=".")
    parser.add_argument("--target", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-clean-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    warnings = []

    if target.exists() and not args.skip_clean_check:
        clean, detail = git_clean(target)
        if not clean:
            output = result("error", "Practice target is not clean.", warnings=[detail], stop_condition="commit_or_stash_practice_changes")
            print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output["summary"])
            return

    copied = copy_tree(source, target, args.dry_run)
    planned, marker_warnings = transform_markers(target if target.exists() else source, args.version, args.dry_run)
    warnings.extend(marker_warnings)
    commit = source_commit(source)

    artifacts = []
    if not args.dry_run:
        meta = target / "docs" / "learn" / "practice-snapshot.json"
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(json.dumps({"version": args.version, "source_commit": commit}, indent=2) + "\n", encoding="utf-8")
        artifacts.append(str(meta))

    status = "success" if planned else "warning"
    output = result(
        status,
        f"Prepared practice snapshot for {args.version}.",
        artifacts=artifacts,
        recommended_reads=["docs/learn/practice-plan.md"],
        next_actions=["Review planned changes", "Run build/tests in practice target after generation"],
        warnings=warnings + ([] if planned else ["No matching practice markers found."]),
        copied_files=len(copied),
        planned_replacements=planned,
        source_commit=commit,
        dry_run=args.dry_run,
    )
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output["summary"])


if __name__ == "__main__":
    main()
