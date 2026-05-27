"""Dense retrieval environment check.

Default mode reports dependency/model/Qdrant readiness without failing the
stage when a local embedding model is absent. Use --strict in deployment.

Run from apps/rag-agent:
    python -B scripts/test/test_dense_retrieval_env.py
    python -B scripts/test/test_dense_retrieval_env.py --strict
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

RAG_ROOT = Path(__file__).resolve().parents[2]
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.config import settings
from app.clients.embedding_client import embedding_client


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    result = {
        "sentence_transformers": "missing",
        "transformers": "missing",
        "torch": "missing",
        "embedding_provider": settings.embedding_provider,
        "embedding_api_url": settings.embedding_api_url,
        "embedding_base_url": settings.embedding_base_url,
        "embedding_effective_url": embedding_client._embedding_url(),
        "embedding_timeout": settings.embedding_timeout,
        "embedding_health_timeout": settings.embedding_health_timeout,
        "embedding_model_local_path": settings.embedding_model_local_path,
        "embedding_model_path_exists": Path(settings.embedding_model_local_path).exists(),
        "embedding_health": {},
        "strict": args.strict,
    }

    try:
        import sentence_transformers
        result["sentence_transformers"] = sentence_transformers.__version__
    except Exception as exc:
        result["sentence_transformers_error"] = str(exc)

    try:
        import transformers
        result["transformers"] = transformers.__version__
    except Exception as exc:
        result["transformers_error"] = str(exc)

    try:
        import torch
        result["torch"] = torch.__version__
    except Exception as exc:
        result["torch_error"] = str(exc)

    result["embedding_health"] = await embedding_client.health_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    ok = (
        result["sentence_transformers"] != "missing"
        and result["transformers"] != "missing"
        and result["torch"] != "missing"
        and result["embedding_health"].get("status") == "ok"
    )
    return 0 if ok or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
