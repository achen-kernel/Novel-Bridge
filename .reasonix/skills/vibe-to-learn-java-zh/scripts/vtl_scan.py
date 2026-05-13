#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


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


def iter_files(root: Path, patterns):
    for pattern in patterns:
        for path in root.rglob(pattern):
            if any(part in SKIP for part in path.parts):
                continue
            if path.is_file():
                yield path


def find_dirs(root: Path, names):
    found = {}
    for path in root.rglob("*"):
        if any(part in SKIP for part in path.parts):
            continue
        if path.is_dir() and path.name.lower() in names and path.name.lower() not in found:
            found[path.name.lower()] = str(path.relative_to(root))
    return found


def find_spring_main(root: Path):
    for path in iter_files(root, ["*.java"]):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "@SpringBootApplication" in text:
            return str(path.relative_to(root))
    return None


def main():
    parser = argparse.ArgumentParser(description="Scan a Java/Vue project and emit a compact profile.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    stack = []
    reads = []
    warnings = []

    if (root / "pom.xml").exists():
        stack.append("maven")
        reads.append("pom.xml")
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        stack.append("gradle")
    if (root / "package.json").exists():
        stack.append("node_frontend")
        reads.append("package.json")
        try:
            pkg = (root / "package.json").read_text(encoding="utf-8", errors="ignore").lower()
            if "vue" in pkg:
                stack.append("vue")
        except OSError:
            pass
    pom = root / "pom.xml"
    if pom.exists() and "spring-boot" in pom.read_text(encoding="utf-8", errors="ignore").lower():
        stack.append("spring_boot")

    main_class = find_spring_main(root)
    if main_class:
        reads.append(main_class)

    backend_dirs = find_dirs(root, {"controller", "service", "mapper", "repository", "entity", "dto", "vo"})
    frontend_dirs = find_dirs(root, {"api", "views", "pages", "router", "store", "stores", "components"})

    if not stack:
        warnings.append("No obvious Maven/Gradle/package.json stack files found.")

    output = result(
        "success",
        "Scanned project structure.",
        recommended_reads=reads[:12],
        next_actions=["Use the profile to create or update docs/learn/current-stage.md"],
        warnings=warnings,
        stack=sorted(set(stack)),
        spring_main=main_class,
        backend_dirs=backend_dirs,
        frontend_dirs=frontend_dirs,
    )
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output["summary"])


if __name__ == "__main__":
    main()
