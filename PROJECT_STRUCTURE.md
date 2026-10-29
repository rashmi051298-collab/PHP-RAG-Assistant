# Project Structure

```text
PHP_RAG_Assistant/
├── app.py                    # Streamlit chat interface
├── ingest.py                 # Repository text ingestion and FAISS indexing
├── rag.py                    # Retrieval, Gemini/NVIDIA routing, and answer handling
├── requirements.txt          # Python dependencies
├── data/                      # Legacy corpus path; excluded from ingestion
├── vectorstore/               # Generated FAISS index and metadata
├── answer_cache.json          # Cached answers
└── generated_outputs/         # Generated PHP downloads
```

`ingest.py` recursively reads supported text-based source, configuration, and
documentation files from the current repository root by default. The legacy `data/`
directory is excluded. Set `KNOWLEDGE_BASE_DIR` to select another local repository.
Relative paths in indexed metadata are retained so responses can refer to source files.

The pipeline splits files into overlapping chunks, embeds them with Hugging Face
`BAAI/bge-base-en-v1.5`, and stores the vectors in FAISS. At query time, FAISS
retrieves relevant chunks, then routes code generation to available Gemini models
and explanations to NVIDIA NIM.
Repeated answers can use the local answer cache, and Gemini model discovery is
cached for 10 minutes per active chat session. The chat displays end-to-end response
time so repository search and remote-provider latency can be distinguished from
cached answers.

The supported source formats and excluded paths are defined in `ingest.py`. Binary
files and common generated/dependency directories are skipped, as are `.env` files
other than `.env.example`.
