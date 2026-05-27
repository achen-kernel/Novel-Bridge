"""
Unified model call interface.

Wraps DeepSeek API and local llama-server (9B) behind a single
`ModelClient` class. Callers select the provider at construction time
and then use the same `.chat()` / `.chat_json()` API regardless of backend.

Usage:

    client = ModelClient(provider="deepseek")   # or "local"
    reply = await client.chat([{"role":"user","content":"..."}])
    structured = await client.chat_json([...])   # returns dict
"""
import logging
import os

logger = logging.getLogger(__name__)


class ModelClient:
    """Unified model call interface with provider abstraction."""

    def __init__(self, provider: str = "local"):
        if provider not in ("local", "deepseek"):
            raise ValueError(f"Unknown provider: {provider!r}. Expected 'local' or 'deepseek'.")
        self.provider = provider

    async def chat(self, messages: list, **kwargs) -> str | dict:
        """Unified chat call. Returns the response string (or fallback dict on error)."""
        if self.provider == "deepseek":
            from app.clients.deepseek_client import deepseek_client
            return await deepseek_client.chat(messages, **kwargs)
        else:
            from app.clients.llama_cpp_client import llama_client
            return await llama_client.chat(messages, **kwargs)

    async def chat_json(self, messages: list, **kwargs) -> dict:
        """Unified JSON-output chat call.

        Automatically loads GBNF grammar for local provider (strict JSON).
        For DeepSeek, no grammar is needed.
        Returns a parsed dict (or an error dict on failure).
        """
        if self.provider == "deepseek":
            from app.clients.deepseek_client import deepseek_client
            return await deepseek_client.chat_json(messages, **kwargs)
        else:
            from app.clients.llama_cpp_client import llama_client
            grammar = self._load_grammar()
            if grammar:
                kwargs.setdefault("grammar", grammar)
            return await llama_client.chat_json(messages, **kwargs)

    @staticmethod
    def _load_grammar() -> str | None:
        """Load the default extraction GBNF grammar file if it exists."""
        grammar_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "extraction_output.gbnf"
        )
        try:
            with open(grammar_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("GBNF grammar file not found at %s", grammar_path)
            return None
