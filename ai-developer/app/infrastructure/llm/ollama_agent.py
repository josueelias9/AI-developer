import os
from typing import List

from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph import graph

from ...domain.entities.code_generation import (
    CodeGenerationRequest,
    CodeGenerationResult,
    GeneratedFile,
)
from ...domain.interfaces.llm_gateway import ILLMGateway
from ...domain.interfaces.code_repository import ICodeRepository


# ── Clean Architecture folder structure reference ─────────────────────────────

_CLEAN_ARCH_STRUCTURE = """
FastAPI Clean Architecture folder structure:

project_root/
├── main.py                            # FastAPI app entry point (creates app, includes routers)
├── requirements.txt                   # Python dependencies
├── README.md                          # Project documentation
└── app/
    ├── domain/
    │   ├── entities/                  # Pure data models (Pydantic BaseModel or dataclasses)
    │   └── interfaces/                # Abstract base classes / protocols (no implementation)
    ├── application/
    │   └── use_cases/                 # Business logic, orchestrates domain + infrastructure
    ├── infrastructure/
    │   ├── database/                  # DB engine, session factory (SQLAlchemy / SQLModel)
    │   └── repositories/              # Concrete implementations of domain interfaces
    └── interfaces/
        └── api/
            ├── routers/               # FastAPI APIRouter handlers
            └── schemas/               # Request / response Pydantic schemas
"""

# ── Orchestrator system prompt ────────────────────────────────────────────────

_ORCHESTRATOR_PROMPT = f"""\
You are an expert software architect that plans and coordinates the creation of \
FastAPI backend projects following Clean Architecture.
{_CLEAN_ARCH_STRUCTURE}
## Your workflow

1. **Plan** the complete list of files needed for the requested backend service.
2. For each file, call `generate_code` with a precise description to produce its content.
3. Call `write_code_file` to persist each generated file to disk.
4. After all files are written, provide a concise summary of what was created.

## Rules

- ALWAYS follow the Clean Architecture folder structure shown above.
- ALWAYS generate every layer: domain, application, infrastructure, interfaces/api.
- ALWAYS include `main.py`, `requirements.txt`, and `README.md`.
- Use `generate_code` to obtain each file's content — never write code inline yourself.
- Use `write_code_file` immediately after `generate_code` to save the file.
- Produce a complete, runnable project; do not skip any file.
"""

# ── Coder system prompt ───────────────────────────────────────────────────────

_CODER_SYSTEM_PROMPT = """\
You are an expert Python and FastAPI developer.
When asked to write a file, return ONLY the complete source code.
Do NOT include markdown fences, explanations, or any commentary.
Write production-ready, fully functional code with type hints throughout.
Follow PEP 8 conventions.
"""


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

    def generate(self, request: CodeGenerationRequest) -> CodeGenerationResult:
        generated_files: List[GeneratedFile] = []
        output_dir = request.output_dir

        # Coder LLM — plain invocation, no tool calling required
        coder_llm = ChatOllama(
            base_url=self._base_url,
            model=self._coder_model,
            temperature=self._temperature,
        )

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
            prompt_parts += ["", "Return ONLY the raw source code with no markdown fences."]

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
            return code

        @tool
        def write_code_file(file_path: str, content: str) -> str:
            """Write source code to a file. Creates parent directories automatically.

            Args:
                file_path: Relative path of the file to create, e.g. 'app/domain/entities/user.py'
                content: Complete source code content of the file
            """
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

        tools = [generate_code, write_code_file, read_code_file, list_directory]

        # Orchestrator LLM — must support tool calling
        orchestrator_llm = ChatOllama(
            base_url=self._base_url,
            model=self._model,
            temperature=self._temperature,
        )

        from langchain.agents.middleware import PIIMiddleware
        agent = create_agent(
            orchestrator_llm,
            tools=tools,
            system_prompt=_ORCHESTRATOR_PROMPT,
            debug=True,
            middleware=[
                # Redact emails in user input before sending to model
                PIIMiddleware(
                    "email",
                    strategy="redact",
                    apply_to_input=True,
                ),
                # Mask credit cards in user input
                PIIMiddleware(
                    "credit_card",
                    strategy="mask",
                    apply_to_input=True,
                ),
                # Block API keys - raise error if detected
                PIIMiddleware(
                    "api_key",
                    detector=r"sk-[a-zA-Z0-9]{32}",
                    strategy="block",
                    apply_to_input=True,
                ),            
            ],
        )

        # For debugging: save the agent's reasoning graph in Mermaid format
        mermaid = agent.get_graph().draw_mermaid()

        mermaid = mermaid.replace("[", "_")
        mermaid = mermaid.replace("]", "_")
        
        with open("graph.mmd", "w") as f:
            f.write(mermaid)

        try:
            result = agent.invoke({
                "messages": [{"role": "user", "content": request.prompt}]
            })
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