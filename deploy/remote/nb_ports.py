#!/usr/bin/env python3
"""
NovelBridge — 远程端口检查工具
读取 ports.env，验证端口是否被占用，输出机器可读的检查结果。

用法:
  python nb_ports.py                          # 检查所有端口
  python nb_ports.py --export runtime.env     # 导出运行时端口 (Demo 阶段固定)
  python nb_ports.py --json                   # JSON 输出

退出码:
  0: 所有端口可用
  1: 至少一个端口被占用
  2: 配置文件读取错误
"""

import os
import re
import socket
import sys
import json
from pathlib import Path

# 默认 ports.env 路径（与本脚本同目录）
_PORTS_ENV = Path(__file__).resolve().parent / "ports.env"


def parse_ports_env(path: Path) -> dict[str, int]:
    """解析 ports.env 文件，返回 {变量名: 端口号} 字典。"""
    if not path.exists():
        print(f"ERROR: 未找到端口配置文件 {path}", file=sys.stderr)
        sys.exit(2)

    ports: dict[str, int] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            # 匹配 LLAMA_PORT=18080 格式
            m = re.match(r"^([A-Z_]+_PORT)=(\d+)$", line)
            if m:
                ports[m.group(1)] = int(m.group(2))
            # 也匹配 NEO4J_HTTP_PORT=17474 等带中间名的
            m2 = re.match(r"^([A-Z_]+_PORT)=(\d+)$", line)
            if m2:
                ports[m2.group(1)] = int(m2.group(2))

    return ports


def check_port(host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    """
    检查端口是否可用。
    返回 (可用, 消息)。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((host, port))
        if result == 0:
            return False, f"端口 {port} 已被占用"
        else:
            return True, f"端口 {port} 可用"
    except socket.error as e:
        return False, f"端口 {port} 检查异常: {e}"
    finally:
        sock.close()


def main():
    # 简单参数解析
    export_path = None
    output_json = False

    for arg in sys.argv[1:]:
        if arg.startswith("--export="):
            export_path = arg.split("=", 1)[1]
        elif arg == "--json":
            output_json = True

    ports = parse_ports_env(_PORTS_ENV)

    if not ports:
        print("WARNING: 未从 ports.env 中解析到任何端口定义", file=sys.stderr)
        sys.exit(2)

    results = {}
    all_ok = True

    for name, port in sorted(ports.items()):
        # 从环境变量名推断端口对应的 host
        host = "127.0.0.1"
        host_var = name.replace("_PORT", "_HOST")
        # 实际 host 从环境变量读取，但 ports.env 中不一定包含 HOST 定义
        # 默认所有端口检查 127.0.0.1
        ok, msg = check_port(host, port)
        if not ok:
            all_ok = False
        results[name] = {
            "port": port,
            "host": host,
            "available": ok,
            "message": msg,
        }

    # 导出运行时环境文件
    if export_path:
        export_file = Path(export_path)
        with open(export_file, "w", encoding="utf-8") as f:
            for name, info in results.items():
                f.write(f"{name}={info['port']}\n")
        print(f"运行时端口已导出到 {export_file}")

    # 输出
    if output_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for name, info in results.items():
            status_icon = "✓" if info["available"] else "✗"
            print(f"  [{status_icon}] {name}: {info['message']}")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
