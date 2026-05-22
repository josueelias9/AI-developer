import os
from typing import List

from ...domain.entities.code_generation import GeneratedFile
from ...domain.interfaces.code_repository import ICodeRepository


class FileCodeRepository(ICodeRepository):
    def save(self, file: GeneratedFile, base_dir: str) -> str:
        full_path = os.path.join(base_dir, file.path)
        parent = os.path.dirname(os.path.abspath(full_path))
        os.makedirs(parent, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as fh:
            fh.write(file.content)
        return full_path

    def read(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except FileNotFoundError:
            return f"[error] File not found: {path}"
        except OSError as exc:
            return f"[error] Could not read file: {exc}"

    def list_files(self, directory: str) -> List[str]:
        try:
            result: List[str] = []
            for root, _dirs, files in os.walk(directory):
                for fname in files:
                    rel = os.path.relpath(os.path.join(root, fname), directory)
                    result.append(rel)
            return sorted(result)
        except OSError:
            return []
