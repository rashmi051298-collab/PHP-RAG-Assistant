import os
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
VECTORSTORE_PATH = "vectorstore"

# Change this only if your PHP source folder is elsewhere.

PHP_SOURCE_DIR = Path(__file__).resolve().parent

EXCLUDED_DIRECTORIES = {
    "vendor",
    "node_modules",
    ".git",
    "vectorstore",
    "__pycache__",
}


def get_embeddings():
    """Create the embedding model used for both indexing and retrieval."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )

def load_php_documents(source_dir: Path) -> list[Document]:
    """Read PHP files while preserving their paths as metadata."""
    if not source_dir.exists():
        raise FileNotFoundError(f"PHP source directory was not found: {source_dir}")

    documents = []

    for php_file in source_dir.rglob("*.php"):
        if any(part in EXCLUDED_DIRECTORIES for part in php_file.parts):
            continue

        try:
            content = php_file.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError as error:
            print(f"Skipping {php_file}: {error}")
            continue

        if not content:
            continue

        relative_path = php_file.relative_to(source_dir).as_posix()
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": relative_path,
                    "file_name": php_file.name,
                    "language": "php",
                },
            )
        )

    return documents


def get_php_splitter():
    """Split PHP around useful code boundaries before falling back to smaller text."""
    return RecursiveCharacterTextSplitter(
        chunk_size=1400,
        chunk_overlap=250,
        keep_separator="start",
        separators=[
            "\n<?php",
            "\nnamespace ",
            "\nuse ",
            "\nclass ",
            "\ninterface ",
            "\ntrait ",
            "\nenum ",
            "\npublic function ",
            "\nprotected function ",
            "\nprivate function ",
            "\nfunction ",
            "\n\n",
            "\n",
            " ",
            "",
        ],
    )


def main():
    print(f"Reading PHP files from: {PHP_SOURCE_DIR}")
    documents = load_php_documents(PHP_SOURCE_DIR)

    if not documents:
        raise RuntimeError("No PHP files were found to ingest.")

    chunks = get_php_splitter().split_documents(documents)

    print(f"Loaded {len(documents)} PHP files.")
    print(f"Created {len(chunks)} PHP code chunks.")
    print(f"Creating embeddings with: {EMBEDDING_MODEL}")

    vectorstore = FAISS.from_documents(chunks, get_embeddings())
    vectorstore.save_local(VECTORSTORE_PATH)

    print(f"Vector store successfully saved to: {VECTORSTORE_PATH}")


if __name__ == "__main__":
    main()