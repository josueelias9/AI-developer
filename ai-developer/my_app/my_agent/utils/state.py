import os

# Pre-defined project structure to scaffold generated backend projects.
SCAFFOLD_DIRS = [
    "app/core",
    "app/api/routes",
    "src/domain/entities",
    "src/application/interfaces",
    "src/application/use_cases",
    "src/infrastructure/database",
    "src/infrastructure/repositories",
    "src/interfaces",
]


def scaffold_project_structure(base_dir: str) -> None:
    """Create the expected folder structure under the output directory."""
    for rel in SCAFFOLD_DIRS:
        os.makedirs(os.path.join(base_dir, rel), exist_ok=True)
