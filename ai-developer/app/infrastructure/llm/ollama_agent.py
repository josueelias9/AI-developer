import os
from typing import List

from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import tool

from ...domain.entities.code_generation import (
    CodeGenerationRequest,
    CodeGenerationResult,
    GeneratedFile,
)
from ...domain.interfaces.llm_gateway import ILLMGateway
from ...domain.interfaces.code_repository import ICodeRepository


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert backend software engineer.
Your task is to generate complete, production-ready backend code based on the user request.

Guidelines:
- Use clean architecture: separate layers for domain, application, infrastructure, and interfaces.
- Write fully functional code, not pseudocode or placeholders.
- Create every file needed: entry point, routes, models, services, repositories, etc.
- Always include a requirements.txt (or equivalent) and a README.md.
- After generating all files, summarise what was created and how to run the project.
"""


# ── Gateway implementation ────────────────────────────────────────────────────

class OllamaAgentGateway(ILLMGateway):
    def __init__(
        self,
        base_url: str,
        model: str,
        code_repository: ICodeRepository,
        temperature: float = 0,
        max_iterations: int = 30,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._code_repository = code_repository
        self._temperature = temperature
        self._max_iterations = max_iterations

    def generate(self, request: CodeGenerationRequest) -> CodeGenerationResult:
        generated_files: List[GeneratedFile] = []
        output_dir = request.output_dir

        # ── Tool functions (closures capture output_dir and generated_files) ──

        @tool
        def write_code_file(file_path: str, content: str) -> str:
            """Write source code to a file. Creates parent directories automatically if they do not exist.

            Args:
                file_path: Relative path of the file to create, e.g. '/app/output/main.py'
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

        tools = [write_code_file, read_code_file, list_directory]

        llm = ChatOllama(
            base_url=self._base_url,
            model=self._model,
            temperature=self._temperature,
        )

        agent = create_agent(
            llm,
            tools=tools,
            system_prompt=_SYSTEM_PROMPT,
            debug=True,
        )

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


# create a simple endpoint that adds two numbers. 
# read and give the content of the file /app/main.py