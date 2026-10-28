import os
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
PROJECT_DIR = Path(__file__).resolve().parent
VECTORSTORE_PATH = PROJECT_DIR / "vectorstore"
DEFAULT_KNOWLEDGE_BASE_DIR = PROJECT_DIR

SUPPORTED_EXTENSIONS = {
    ".adoc",
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".cjs",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".cxx",
    ".dart",
    ".ex",
    ".exs",
    ".go",
    ".gql",
    ".graphql",
    ".h",
    ".hcl",
    ".hpp",
    ".html",
    ".ini",
    ".ipynb",
    ".java",
    ".js",
    ".jsx",
    ".json",
    ".jsonl",
    ".kt",
    ".lock",
    ".markdown",
    ".md",
    ".mdown",
    ".mdx",
    ".php",
    ".pl",
    ".properties",
    ".proto",
    ".py",
    ".r",
    ".rb",
    ".rs",
    ".rst",
    ".scala",
    ".scss",
    ".sh",
    ".svelte",
    ".sql",
    ".swift",
    ".tf",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}

SUPPORTED_FILENAMES = {
    ".dockerignore",
    ".editorconfig",
    ".env.example",
    ".gitattributes",
    ".gitignore",
    "authors",
    "brewfile",
    "changelog",
    "code_of_conduct",
    "cmakelists.txt",
    "contributing",
    "dockerfile",
    "gemfile",
    "go.mod",
    "go.sum",
    "justfile",
    "license",
    "makefile",
    "notice",
    "pnpm-workspace.yaml",
    "procfile",
    "rakefile",
    "readme",
    "vagrantfile",
    ".nvmrc",
    ".prettierrc",
    ".python-version",
    ".ruby-version",
}

EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "data",
    "dist",
    "generated_outputs",
    "node_modules",
    "venv",
    "vendor",
    "vectorstore",
}


def get_embeddings():
    """Create the embedding model used for both indexing and retrieval."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def is_supported_text_file(file_path: Path) -> bool:
    """Return whether a repository file is a supported text/document format."""
    return (
        file_path.suffix.lower() in SUPPORTED_EXTENSIONS
        or file_path.name.lower() in SUPPORTED_FILENAMES
    )


def load_knowledge_documents(source_dir: Path) -> list[Document]:
    """Load supported text files while preserving repository paths as metadata."""
    if not source_dir.exists():
        raise FileNotFoundError(
            f"Knowledge base directory was not found: {source_dir}"
        )
    if not source_dir.is_dir():
        raise NotADirectoryError(
            f"Knowledge base path is not a directory: {source_dir}"
        )

    documents = []

    def raise_walk_error(error):
        raise error

    for current_root, directory_names, file_names in os.walk(
        source_dir,
        topdown=True,
        onerror=raise_walk_error,
    ):
        directory_names[:] = [
            name
            for name in directory_names
            if name.lower() not in EXCLUDED_DIRECTORIES
        ]

        for file_name in file_names:
            source_file = Path(current_root) / file_name
            if not is_supported_text_file(source_file):
                continue

            normalized_name = source_file.name.lower()
            if normalized_name == ".env" or (
                normalized_name.startswith(".env.")
                and normalized_name != ".env.example"
            ):
                continue

            try:
                content = source_file.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).strip()
            except OSError as error:
                print(f"Skipping {source_file}: {error}")
                continue

            if not content or "\x00" in content:
                continue

            relative_source = source_file.relative_to(source_dir).as_posix()
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": relative_source,
                        "file_name": source_file.name,
                        "file_type": source_file.suffix.lower() or "text",
                    },
                )
            )

    return documents


def get_knowledge_splitter():
    """Split repository text into overlapping chunks for semantic retrieval."""
    return RecursiveCharacterTextSplitter(
        chunk_size=1400,
        chunk_overlap=250,
        keep_separator="start",
        separators=["\n\n", "\n", " ", ""],
    )


def get_knowledge_base_dir() -> Path:
    """Resolve the corpus directory from the environment or the default location."""
    configured_path = os.getenv("KNOWLEDGE_BASE_DIR")
    source_dir = Path(configured_path) if configured_path else DEFAULT_KNOWLEDGE_BASE_DIR
    if not source_dir.is_absolute():
        source_dir = PROJECT_DIR / source_dir
    return source_dir.resolve()


def main():
    source_dir = get_knowledge_base_dir()
    print(f"Reading repository knowledge files from: {source_dir}")
    documents = load_knowledge_documents(source_dir)

    if not documents:
        raise RuntimeError(
            "No supported text files were found in the selected knowledge base: "
            f"{source_dir}"
        )

    chunks = get_knowledge_splitter().split_documents(documents)

    print(f"Loaded {len(documents)} knowledge files.")
    print(f"Created {len(chunks)} text chunks.")
    print(f"Creating embeddings with: {EMBEDDING_MODEL}")

    vectorstore = FAISS.from_documents(chunks, get_embeddings())
    vectorstore.save_local(str(VECTORSTORE_PATH))

    print(f"Vector store successfully saved to: {VECTORSTORE_PATH}")


if __name__ == "__main__":
    main()
