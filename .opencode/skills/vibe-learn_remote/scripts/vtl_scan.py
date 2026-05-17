#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


SKIP = {".git", "target", "node_modules", "dist", "build", ".idea", ".gradle"}
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


def load_adapter(root: Path):
    path = root / ADAPTER_PATH
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": f"Invalid {ADAPTER_PATH}: {exc}"}


def rel(path: Path, root: Path):
    return str(path.relative_to(root)).replace("\\", "/")


def skipped(path: Path):
    return any(part in SKIP for part in path.parts)


def iter_files(root: Path, patterns):
    for pattern in patterns:
        for path in root.rglob(pattern):
            if skipped(path.relative_to(root)):
                continue
            if path.is_file():
                yield path


def find_dirs(root: Path, names):
    found = {}
    for path in root.rglob("*"):
        if skipped(path.relative_to(root)):
            continue
        if path.is_dir() and path.name.lower() in names and path.name.lower() not in found:
            found[path.name.lower()] = rel(path, root)
    return found


def find_spring_main(root: Path):
    for path in iter_files(root, ["*.java"]):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "@SpringBootApplication" in text:
            return rel(path, root)
    return None


def read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def discover_maven_services(root: Path):
    services = []
    for pom in iter_files(root, ["pom.xml"]):
        text = read_text(pom).lower()
        service = {
            "root": rel(pom.parent, root),
            "build": "maven",
            "spring_boot": "spring-boot" in text,
            "descriptor": rel(pom, root),
        }
        services.append(service)
    return services


def discover_gradle_services(root: Path):
    services = []
    for gradle in list(iter_files(root, ["build.gradle"])) + list(iter_files(root, ["build.gradle.kts"])):
        text = read_text(gradle).lower()
        service = {
            "root": rel(gradle.parent, root),
            "build": "gradle",
            "spring_boot": "spring-boot" in text,
            "descriptor": rel(gradle, root),
        }
        services.append(service)
    return services


def discover_node_services(root: Path):
    services = []
    for pkg_path in iter_files(root, ["package.json"]):
        text = read_text(pkg_path).lower()
        service = {
            "root": rel(pkg_path.parent, root),
            "build": "node",
            "vue": "vue" in text,
            "vite": "vite" in text,
            "descriptor": rel(pkg_path, root),
        }
        services.append(service)
    return services


def discover_python_services(root: Path):
    markers = list(iter_files(root, ["pyproject.toml"])) + list(iter_files(root, ["requirements.txt"]))
    services = []
    seen = set()
    for marker in markers:
        service_root = marker.parent
        if service_root in seen:
            continue
        seen.add(service_root)
        text = read_text(marker).lower()
        services.append({
            "root": rel(service_root, root),
            "build": "python",
            "fastapi": "fastapi" in text,
            "descriptor": rel(marker, root),
        })
    return services


def choose_roots(services, adapter):
    roots = {
        "backend_root": None,
        "frontend_root": None,
        "rag_root": None,
    }
    if adapter and not adapter.get("_error"):
        roots.update({
            "backend_root": adapter.get("backend_root"),
            "frontend_root": adapter.get("frontend_root"),
            "rag_root": adapter.get("rag_root"),
        })
    if not roots["backend_root"]:
        for service in services["java"]:
            if service.get("spring_boot"):
                roots["backend_root"] = service["root"]
                break
    if not roots["frontend_root"]:
        for service in services["node"]:
            if service.get("vue") or service.get("vite"):
                roots["frontend_root"] = service["root"]
                break
    if not roots["rag_root"]:
        for service in services["python"]:
            if service.get("fastapi") or "rag" in service["root"].lower():
                roots["rag_root"] = service["root"]
                break
    return roots


def main():
    parser = argparse.ArgumentParser(description="Scan a Java/Vue project and emit a compact profile.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    reads = []
    warnings = []
    adapter = load_adapter(root)
    if adapter and adapter.get("_error"):
        warnings.append(adapter["_error"])
    services = {
        "java": discover_maven_services(root) + discover_gradle_services(root),
        "node": discover_node_services(root),
        "python": discover_python_services(root),
    }
    roots = choose_roots(services, adapter)
    stack = []
    for service in services["java"]:
        stack.append(service["build"])
        if service.get("spring_boot"):
            stack.append("spring_boot")
        reads.append(service["descriptor"])
    for service in services["node"]:
        stack.append("node_frontend")
        if service.get("vue"):
            stack.append("vue")
        if service.get("vite"):
            stack.append("vite")
        reads.append(service["descriptor"])
    for service in services["python"]:
        stack.append("python")
        if service.get("fastapi"):
            stack.append("fastapi")
        reads.append(service["descriptor"])

    main_class = find_spring_main(root)
    if main_class:
        reads.append(main_class)

    backend_dirs = find_dirs(root, {"controller", "service", "mapper", "repository", "entity", "dto", "vo"})
    frontend_dirs = find_dirs(root, {"api", "views", "pages", "router", "store", "stores", "components"})

    if not stack:
        warnings.append("No obvious Maven/Gradle/package.json/pyproject/requirements stack files found.")
    if not (root / ADAPTER_PATH).exists():
        warnings.append(f"No {ADAPTER_PATH}; create one if service roots are wrong.")

    output = result(
        "success",
        "Scanned project structure.",
        recommended_reads=reads[:12],
        next_actions=[
            "Use the profile to create or update docs/learn_remote/current-stage.md",
            f"Create {ADAPTER_PATH} if detected roots are wrong",
        ],
        warnings=warnings,
        stack=sorted(set(stack)),
        service_roots=roots,
        services=services,
        adapter=adapter,
        spring_main=main_class,
        backend_dirs=backend_dirs,
        frontend_dirs=frontend_dirs,
    )
    print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else output["summary"])


if __name__ == "__main__":
    main()
