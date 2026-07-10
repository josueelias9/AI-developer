import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from my_agent.utils.nodes import CODER_SYSTEM_PROMPT


def _resolve_path(output_dir: str, relative_path: str) -> str:
    root = os.path.realpath(output_dir)
    resolved = os.path.realpath(os.path.join(output_dir, relative_path))
    if resolved != root and not resolved.startswith(root + os.sep):
        raise PermissionError(
            f"Saving outside '{output_dir}' is not allowed. Attempted path: {resolved}"
        )
    return resolved


def build_tools(coder_llm, output_dir: str):
    @tool
    def generate_code(file_path: str, description: str, context: str = "") -> str:
        """Generate source code for a specific file using the coder model."""
        prompt_parts = [
            f"Generate the complete source code for the file: {file_path}",
            "",
            f"Description: {description}",
        ]
        if context:
            prompt_parts += ["", f"Context:\n{context}"]
        prompt_parts += ["", "Return only raw source code."]

        response = coder_llm.invoke(
            [
                SystemMessage(content=CODER_SYSTEM_PROMPT),
                HumanMessage(content="\n".join(prompt_parts)),
            ]
        )
        code = response.content

        if isinstance(code, list):
            code = "".join(str(part) for part in code)

        if isinstance(code, str) and code.startswith("```"):
            lines = code.splitlines()
            end = len(lines) - 1 if lines and lines[-1].strip() == "```" else len(lines)
            code = "\n".join(lines[1:end])

        return str(code)

    @tool
    def write_code_file(file_path: str, content: str) -> str:
        """Write source code to a file under the output directory."""
        full_path = _resolve_path(output_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return f"Written: {full_path}"

    @tool
    def read_code_file(file_path: str) -> str:
        """Read and return an existing file under the output directory."""
        full_path = _resolve_path(output_dir, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as fh:
                return fh.read()
        except FileNotFoundError:
            return f"[error] File not found: {file_path}"
        except OSError as exc:
            return f"[error] Could not read file: {exc}"

    @tool
    def list_directory(directory: str = ".") -> str:
        """List files recursively under a directory within the output directory."""
        target_dir = _resolve_path(output_dir, directory)
        result = []
        for root, _dirs, files in os.walk(target_dir):
            for fname in files:
                abs_path = os.path.join(root, fname)
                result.append(os.path.relpath(abs_path, target_dir))
        return "\n".join(sorted(result)) if result else "(empty)"

    return [
        generate_code,
        # write_code_file,
        # read_code_file,
        # list_directory
    ]
