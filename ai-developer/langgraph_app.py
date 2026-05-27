"""
Entry point for LangGraph Studio.

Exposes `graph` as a compiled LangGraph agent that Studio can load and run.
Reads configuration from environment variables so that no runtime parameters
are required at import time.

Required env vars:
  OLLAMA_HOST      – Ollama server URL  (e.g. http://localhost:11434)
  OLLAMA_MODEL     – Orchestrator model (e.g. qwen2.5:7b)
  OLLAMA_CODER     – Coder model        (e.g. qwen2.5-coder:7b)
  OUTPUT_DIR       – Directory where generated files are written
"""

import os
import tempfile

from app.infrastructure.repositories.file_code_repository import FileCodeRepository
from app.infrastructure.llm.ollama_agent import OllamaAgentGateway

# ── Read config from environment ──────────────────────────────────────────────

_base_url = os.getenv("OLLAMA_HOST")
_model = os.getenv("OLLAMA_MODEL")
_coder_model = os.getenv("OLLAMA_CODER")
_output_dir = os.getenv("OUTPUT_DIR")

os.makedirs(_output_dir, exist_ok=True)

# ── Build the agent graph ─────────────────────────────────────────────────────

_code_repository = FileCodeRepository()
_gateway = OllamaAgentGateway(
    base_url=_base_url,
    model=_model,
    coder_model=_coder_model,
    code_repository=_code_repository,
)

# `graph` is the compiled LangGraph graph that Studio will load.
graph = _gateway.build_graph(_output_dir)
