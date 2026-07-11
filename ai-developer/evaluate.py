"""
https://docs.langchain.com/langsmith/evaluate-rag-tutorial

LangSmith evaluation for the AI Backend Code Generator.

Required environment variables:
  LANGCHAIN_API_KEY      — LangSmith API key
  LANGCHAIN_TRACING_V2   — set to "true" to enable tracing (optional, for live runs)
  OLLAMA_BASE_URL        — defaults to http://localhost:11434
  OLLAMA_MODEL           — defaults to codellama
"""

import os
import tempfile

from langsmith import Client
from langsmith.evaluation import evaluate
from langsmith.schemas import Example, Run

from my_app.my_agent.agent import graph

# ── Dataset ───────────────────────────────────────────────────────────────────

client = Client()

examples = [
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

dataset_name = "backend-code-generation-eval"

# ── Dataset setup ─────────────────────────────────────────────────────────────


existing = {d.name for d in client.list_datasets()}
if dataset_name not in existing:
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Prompts for evaluating backend code generation quality.",
    )
    client.create_examples(
        inputs=[{"prompt": ex["prompt"]} for ex in examples],
        outputs=[{"expected_files": ex["expected_files"]} for ex in examples],
        dataset_id=dataset.id,
    )
    print(f"Dataset '{dataset_name}' created ({len(examples)} examples).")
else:
    print(f"Using existing dataset '{dataset_name}'.")

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


# ── Target function ───────────────────────────────────────────────────────────


def _list_files(base_dir: str) -> list[str]:
    result: list[str] = []
    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            abs_path = os.path.join(root, fname)
            result.append(os.path.relpath(abs_path, base_dir))
    return sorted(result)


def target(inputs: dict) -> dict:
    with tempfile.TemporaryDirectory() as output_dir:
        agent = graph

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
            # TODO: ai-generated-code directory or temp? decide
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


# ── Entry point ───────────────────────────────────────────────────────────────


experiment_results = evaluate(
    target,
    data=dataset_name,
    evaluators=[
        generation_success,
        min_files_generated,
        expected_files_coverage,
        has_readme,
    ],
    experiment_prefix="codegen-eval",
    metadata={"info": "testing model"},
)

print("\n── Evaluation Results ───────────────────────────────────────────")
for r in experiment_results:
    print(r)
