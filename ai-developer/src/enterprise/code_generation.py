from dataclasses import dataclass, field
from typing import List


@dataclass
class CodeGenerationRequest:
    prompt: str
    output_dir: str = "."


@dataclass
class GeneratedFile:
    path: str
    content: str
    language: str = "python"


@dataclass
class CodeGenerationResult:
    request: CodeGenerationRequest
    files: List[GeneratedFile] = field(default_factory=list)
    success: bool = False
    summary: str = ""
    error: str = ""
