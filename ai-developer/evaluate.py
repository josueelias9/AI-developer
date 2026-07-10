"""
LangSmith evaluation for the AI Backend Code Generator.

Required environment variables:
  LANGCHAIN_API_KEY      — LangSmith API key
  LANGCHAIN_TRACING_V2   — set to "true" to enable tracing (optional, for live runs)
  OLLAMA_BASE_URL        — defaults to http://localhost:11434
  OLLAMA_MODEL           — defaults to codellama
"""

import os
import sys
import tempfile
from pathlib import Path

from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langsmith import Client
from langsmith.evaluation import evaluate
from langsmith.schemas import Example, Run

# Ensure my-app package is importable from the root workspace.
MY_APP_DIR = Path(__file__).resolve().parent / "my-app"
if str(MY_APP_DIR) not in sys.path:
    sys.path.insert(0, str(MY_APP_DIR))

from my_app.my_agent.utils.nodes import get_orchestrator_prompt
from my_app.my_agent.utils.state import scaffold_project_structure
from my_app.my_agent.utils.tools import build_tools

# ── Dataset ───────────────────────────────────────────────────────────────────

DATASET_NAME = "backend-code-generation-eval"

_EXAMPLES = [
    {
        "prompt": "Create a REST API with FastAPI that manages a todo list with CRUD operations.",
        "expected_files": ["main.py", "requirements.txt", "README.md"],
    },
    # {
    #     "prompt": "Build a Flask API with a /health endpoint that returns {\"status\": \"ok\"}.",
    #     "expected_files": ["main.py", "requirements.txt"],
    # },
    # {
    #     "prompt": (
    #         "Create a Python script that connects to PostgreSQL "
    #         "and provides CRUD operations for a users table."
    #     ),
    #     "expected_files": ["main.py", "requirements.txt"],
    # },
]


# ── Target function ───────────────────────────────────────────────────────────


def _build_target():
    base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    coder_model = os.getenv("OLLAMA_CODER", "qwen2.5-coder:7b")

    def _list_files(base_dir: str) -> list[str]:
        result: list[str] = []
        for root, _dirs, files in os.walk(base_dir):
            for fname in files:
                abs_path = os.path.join(root, fname)
                result.append(os.path.relpath(abs_path, base_dir))
        return sorted(result)

    def target(inputs: dict) -> dict:
        with tempfile.TemporaryDirectory() as output_dir:
            os.environ["OUTPUT_DIR"] = output_dir
            scaffold_project_structure(output_dir)

            coder_llm = ChatOllama(
                base_url=base_url,
                model=coder_model,
                temperature=0,
            )
            orchestrator_llm = ChatOllama(
                base_url=base_url,
                model=model,
                temperature=0,
            )

            tools = build_tools(coder_llm=coder_llm, output_dir=output_dir)
            agent = create_agent(
                orchestrator_llm,
                tools=tools,
                system_prompt=get_orchestrator_prompt(),
                debug=True,
            )

            try:
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": inputs["prompt"]}]}
                )
                messages = result.get("messages", [])
                summary = ""
                if messages:
                    last_msg = messages[-1]
                    summary = getattr(last_msg, "content", "")
                    if isinstance(summary, list):
                        summary = "".join(str(part) for part in summary)

                generated_files = _list_files(output_dir)
                return {
                    "success": True,
                    "files": generated_files,
                    "file_count": len(generated_files),
                    "summary": str(summary),
                    "error": None,
                }
            except Exception as exc:
                generated_files = _list_files(output_dir)
                return {
                    "success": False,
                    "files": generated_files,
                    "file_count": len(generated_files),
                    "summary": "",
                    "error": str(exc),
                }

    return target


# ── Evaluators ────────────────────────────────────────────────────────────────


def generation_success(run: Run, example: Example) -> dict:
    """Score 1 if the agent completed without errors, 0 otherwise."""
    score = 1 if (run.outputs or {}).get("success") else 0
    return {"key": "generation_success", "score": score}


def min_files_generated(run: Run, example: Example) -> dict:
    """Score 1 if at least 2 files were generated (code + requirements)."""
    score = 1 if (run.outputs or {}).get("file_count", 0) >= 2 else 0
    return {"key": "min_files_generated", "score": score}


def expected_files_coverage(run: Run, example: Example) -> dict:
    """Ratio of expected filenames found anywhere in the generated file paths."""
    generated = (run.outputs or {}).get("files", [])
    expected = (example.outputs or {}).get("expected_files", [])
    if not expected:
        return {"key": "expected_files_coverage", "score": 1.0}
    matched = sum(1 for exp in expected if any(exp in gen for gen in generated))
    return {"key": "expected_files_coverage", "score": matched / len(expected)}


def has_readme(run: Run, example: Example) -> dict:
    """Score 1 if a README file was generated."""
    files = (run.outputs or {}).get("files", [])
    score = 1 if any("readme" in f.lower() for f in files) else 0
    return {"key": "has_readme", "score": score}


# ── Dataset setup ─────────────────────────────────────────────────────────────


def _setup_dataset(client: Client) -> str:
    existing = {d.name for d in client.list_datasets()}
    if DATASET_NAME not in existing:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Prompts for evaluating backend code generation quality.",
        )
        client.create_examples(
            inputs=[{"prompt": ex["prompt"]} for ex in _EXAMPLES],
            outputs=[{"expected_files": ex["expected_files"]} for ex in _EXAMPLES],
            dataset_id=dataset.id,
        )
        print(f"Dataset '{DATASET_NAME}' created ({len(_EXAMPLES)} examples).")
    else:
        print(f"Using existing dataset '{DATASET_NAME}'.")
    return DATASET_NAME


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    client = Client()
    dataset_name = _setup_dataset(client)

    results = evaluate(
        _build_target(),
        data=dataset_name,
        evaluators=[
            generation_success,
            min_files_generated,
            expected_files_coverage,
            has_readme,
        ],
        experiment_prefix="codegen-eval",
        metadata={"model": os.getenv("OLLAMA_MODEL", "codellama")},
    )

    print("\n── Evaluation Results ───────────────────────────────────────────")
    for r in results:
        print(r)


if __name__ == "__main__":
    main()
