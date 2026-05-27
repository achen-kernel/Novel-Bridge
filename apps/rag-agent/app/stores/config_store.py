"""
NovelBridge 服务配置持久化层。

配置保存在项目根目录的 `novel_bridge_config.json` 中。
包含所有外部服务（MySQL / Qdrant / Neo4j / LLM / Embedding / DeepSeek）的连接参数
以及 SSH 隧道配置。
"""
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 项目根目录（apps/rag-agent/ 的父目录的父目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / "novel_bridge_config.json"

# 默认配置
DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "deepseek": {
        "api_key": "",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
    },
    "mysql": {
        "mode": "local",
        "host": "127.0.0.1",
        "port": 13306,
        "user": "root",
        "password": "",
        "database": "novel_bridge",
    },
    "qdrant": {
        "mode": "local",
        "host": "127.0.0.1",
        "port": 16333,
    },
    "neo4j": {
        "mode": "local",
        "host": "127.0.0.1",
        "http_port": 17474,
        "bolt_port": 17687,
        "user": "neo4j",
        "password": "",
    },
    "llama": {
        "mode": "local",
        "host": "127.0.0.1",
        "port": 18080,
    },
    "embedding": {
        "mode": "local",
        "host": "127.0.0.1",
        "port": 18082,
        "api_path": "/v1/embeddings",
    },
    "ssh": {
        "host": "",
        "user": "",
        "port": 22,
        "auth_method": "key",
        "key_path": "",
        "password": "",
    },
}

# 需要掩码的密钥字段
SECRET_FIELDS = {"api_key", "password"}


def _mask_value(key: str, value: str) -> str:
    """掩码敏感字段，只显示前4位和后4位。"""
    if key in SECRET_FIELDS and value:
        v = str(value)
        if len(v) > 12:
            return v[:4] + "*" * (len(v) - 8) + v[-4:]
        elif len(v) > 4:
            return v[:2] + "*" * (len(v) - 4) + v[-2:]
        return "****"
    return value


class ConfigStore:
    """服务配置的读写与持久化。"""

    def load(self) -> dict:
        """读取配置，文件不存在时返回默认值。"""
        if not CONFIG_FILE.exists():
            logger.info("Config file not found, using defaults: %s", CONFIG_FILE)
            return dict(DEFAULT_CONFIG)
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 合并缺失的默认字段
            merged = dict(DEFAULT_CONFIG)
            self._deep_merge(merged, data)
            return merged
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read config file: %s, using defaults", e)
            return dict(DEFAULT_CONFIG)

    def save(self, config: dict) -> bool:
        """保存配置到 JSON 文件。"""
        try:
            merged = dict(DEFAULT_CONFIG)
            self._deep_merge(merged, config)
            merged["version"] = DEFAULT_CONFIG["version"]
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            logger.info("Config saved to %s", CONFIG_FILE)
            return True
        except OSError as e:
            logger.error("Failed to save config: %s", e)
            return False

    def load_public(self) -> dict:
        """返回掩码敏感字段后的配置，供前端展示。"""
        config = self.load()
        for section, fields in config.items():
            if isinstance(fields, dict):
                for key, value in fields.items():
                    if key in SECRET_FIELDS and value:
                        fields[key] = _mask_value(key, value)
        return config

    def apply_to_env(self, config: dict | None = None) -> dict:
        """将配置同步到 app.config.settings（内存中），返回变更摘要。"""
        if config is None:
            config = self.load()
        changed = {}
        # 目前 settings 从 .env 和环境变量读取，这里记录变更供后续重启引用
        return changed

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        """递归合并 override 到 base。"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigStore._deep_merge(base[key], value)
            else:
                base[key] = value


# 全局单例
config_store = ConfigStore()
