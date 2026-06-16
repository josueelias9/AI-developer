import os
from typing import List

from langgraph import graph
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware, ModelCallLimitMiddleware
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import InMemorySaver
from deepagents import create_deep_agent
from deepagents.middleware.filesystem import (
    FilesystemMiddleware,
    FilesystemPermission,
)
from deepagents.backends import (
    CompositeBackend,
    StateBackend,
    FilesystemBackend,
    StoreBackend,
)


from ...domain.entities.code_generation import (
    CodeGenerationRequest,
    CodeGenerationResult,
    GeneratedFile,
)
from ...domain.interfaces.llm_gateway import ILLMGateway
from ...domain.interfaces.code_repository import ICodeRepository


from prompts import _ORCHESTRATOR_PROMPT, _CODER_SYSTEM_PROMPT


# ── Pre-defined project structure ───────────────────────────────────────────

_BASE_DIR = "/ai-generated-code"

_SCAFFOLD_DIRS = [
    "app/core",
    "app/api/routes",
    "src/domain/entities",
    "src/application/interfaces",
    "src/application/use_cases",
    "src/infrastructure/database",
    "src/infrastructure/repositories",
    "src/interfaces",
]


def _scaffold_project_structure(base_dir: str) -> None:
    """Pre-create the Clean Architecture directory tree under base_dir."""
    for rel in _SCAFFOLD_DIRS:
        os.makedirs(os.path.join(base_dir, rel), exist_ok=True)




# ── Gateway implementation ────────────────────────────────────────────────────


class OllamaAgentGateway(ILLMGateway):
    def __init__(
        self,
        base_url: str,
        model: str,
        coder_model: str,
        code_repository: ICodeRepository,
        temperature: float = 0,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._coder_model = coder_model
        self._code_repository = code_repository
        self._temperature = temperature

    def _create_agent(self, generated_files: List[GeneratedFile]):
        """Build and return the compiled LangGraph agent for a given output directory."""

        # Coder LLM — plain invocation, no tool calling required
        coder_llm = ChatOllama(
            base_url=self._base_url,
            model=self._coder_model,
            temperature=self._temperature,
        )

        output_dir = _BASE_DIR

        # ── Tool functions ────────────────────────────────────────────────────

        @tool
        def generate_code(file_path: str, description: str, context: str = "") -> str:
            """Generate source code for a specific file using a specialised code-generation model.

            Args:
                file_path: Relative path of the file to generate, e.g. 'app/domain/entities/user.py'
                description: Detailed description of what this file must contain and do
                context: Optional extra context (related files, data models, endpoints, etc.)
            """
            prompt_parts = [
                f"Generate the complete source code for the file: `{file_path}`",
                "",
                f"Description: {description}",
            ]
            if context:
                prompt_parts += ["", f"Context:\n{context}"]
            prompt_parts += [
                "",
                "Return ONLY the raw source code with no markdown fences.",
            ]
            messages = [
                SystemMessage(content=_CODER_SYSTEM_PROMPT),
                HumanMessage(content="\n".join(prompt_parts)),
            ]
            response = coder_llm.invoke(messages)
            code: str = response.content
            # Strip accidental markdown fences if the model added them
            if code.startswith("```"):
                lines = code.splitlines()
                end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                code = "\n".join(lines[1:end])
            return f"""
```{file_path.rsplit('/', 1)[-1]}
{code}
```
"""

        @tool
        def write_code_file(file_path: str, content: str) -> str:
            """Write source code to a file. Creates parent directories automatically.

            Args:
                file_path: Relative path of the file to create, e.g. 'app/domain/entities/user.py'
                content: Complete source code content of the file
            """
            # Resolve the target path and enforce it stays within _BASE_DIR
            resolved = os.path.realpath(os.path.join(output_dir, file_path))
            if not resolved.startswith(os.path.realpath(output_dir) + os.sep) and resolved != os.path.realpath(output_dir):
                raise PermissionError(
                    f"Saving outside '{output_dir}' is not allowed. "
                    f"Attempted path: {resolved}"
                )
            gf = GeneratedFile(path=file_path, content=content)
            saved = self._code_repository.save(gf, output_dir)
            generated_files.append(gf)
            return f"Written: {saved}"

        @tool
        def read_code_file(file_path: str) -> str:
            """Read and return the contents of an existing file.

            Args:
                file_path: Relative path of the file to read
            """
            full_path = os.path.join(output_dir, file_path)
            return self._code_repository.read(full_path)

        @tool
        def list_directory(directory: str = ".") -> str:
            """List all files inside a directory recursively.

            Args:
                directory: Relative path of the directory to list
            """
            full_path = os.path.join(output_dir, directory)
            files = self._code_repository.list_files(full_path)
            return "\n".join(files) if files else "(empty)"

        # Orchestrator LLM — must support tool calling
        orchestrator_llm = ChatOllama(
            base_url=self._base_url,
            model=self._model,
            temperature=self._temperature,
        )


        _scaffold_project_structure(_BASE_DIR)
        return create_agent(
            orchestrator_llm,
            tools=[generate_code],
            system_prompt=_ORCHESTRATOR_PROMPT,
            debug=True,
            middleware=[
                # TodoListMiddleware(),
                FilesystemMiddleware(
                    backend=FilesystemBackend(
                        root_dir="/ai-generated-code",
                        virtual_mode=True,
                    ),
                    # _permissions=[
                    #     # Allow all operations inside /ai-generated-code
                    #     FilesystemPermission(
                    #         operations=["read", "write"],
                    #         paths=["/ai-generated-code/**", "/ai-generated-code"],
                    #         mode="allow",
                    #     ),
                    #     # Deny writes anywhere else (reads outside are still allowed)
                    #     FilesystemPermission(
                    #         operations=["write"],
                    #         paths=["/**"],
                    #         mode="deny",
                    #     ),
                    # ],
                ),
            ],
        )

    def build_graph(self):
        """Return the compiled LangGraph agent for use in LangGraph Studio."""
        return self._create_agent([])

    def generate(self, request: CodeGenerationRequest) -> CodeGenerationResult:
        generated_files: List[GeneratedFile] = []

        agent = self._create_agent(generated_files)

        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": request.prompt}]}
            )
            last_msg = result["messages"][-1]
            summary = last_msg.content if hasattr(last_msg, "content") else ""
            return CodeGenerationResult(
                request=request,
                files=generated_files,
                success=True,
                summary=summary,
            )
        except Exception as exc:
            return CodeGenerationResult(
                request=request,
                files=generated_files,
                success=False,
                error=str(exc),
            )
