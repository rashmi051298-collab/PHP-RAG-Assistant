# PHP Vibe Coding Assistant - Quick Start

## 1. Install dependencies

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
$env:GEMINI_API_KEY="YOUR_API_KEY"
$env:NVIDIA_API_KEY="YOUR_NVIDIA_API_KEY"
```

Gemini is used for PHP code/project generation; NVIDIA NIM is used for explanations.
Set both keys in the same terminal before starting Streamlit. On macOS/Linux,
activate with `source venv/bin/activate` and export both environment variables.
The default NVIDIA model is `nvidia/nemotron-3.5-lightning-30b-a3b`. In PowerShell, set
`$env:NVIDIA_MODEL="nvidia/nemotron-3.5-lightning-30b-a3b"` if your environment still has
an older model ID configured, then restart Streamlit.

## 2. Use the current local repository

The indexer uses the `PHP-RAG-Assistant` checkout you are already in as its
knowledge base. No cloning or copying is needed. It skips the legacy `data/`
directory, generated files, virtual environments, and dependency folders.

To index a different local checkout, set `KNOWLEDGE_BASE_DIR` to its path before
running ingestion.

The indexer processes supported text-based source files and documentation (for
example Python, PHP, JavaScript/TypeScript, Java, Go, Rust, Markdown, JSON, YAML,
TOML, SQL, and plain text). It skips binary files, common generated/dependency
folders, and `.env` files except `.env.example`.

## 3. Build the vector store

```bash
python ingest.py
```

This creates or updates the FAISS index in `vectorstore/`, using Hugging Face
`BAAI/bge-base-en-v1.5` embeddings. Re-run ingestion whenever the knowledge base
changes.

## 4. Start chatting

```bash
streamlit run app.py
```

The assistant retrieves relevant repository context with FAISS and uses Gemini
for code-generation requests and NVIDIA for explanations. Ask PHP questions,
request code, or describe a full project.
For project requests, it can package path-labeled files into a ZIP download.
Each answer shows its end-to-end response time. Remote model/network time varies;
repeated prompts can use a saved answer without contacting a model. Gemini model
discovery is cached for 10 minutes during the active chat session.
Example prompts:

- "Summarize this repository's architecture."
- "Which files implement the main user workflow?"
- "Where is configuration loaded?"
- "Explain how this module is tested."
- "Build a PHP inventory app with login, CRUD, validation, tests, and setup instructions."

## Troubleshooting

- **Vectorstore not found:** Run `python ingest.py` first.
- **No supported text files found:** Verify the current repository contains supported
  text/code files, or set `KNOWLEDGE_BASE_DIR`.
- **Gemini API key error:** Set `GEMINI_API_KEY` in the same terminal before
  requesting code generation.
- **NVIDIA API key error:** Set `NVIDIA_API_KEY` in the same terminal before
  asking for explanations.
- **NVIDIA HTTP 410:** The selected model or hosted service may no longer be
  available. Choose an active model from NVIDIA's API Catalog, set
  `$env:NVIDIA_MODEL="model-id"` in PowerShell, then restart Streamlit.
- **Need a different repository:** Set `KNOWLEDGE_BASE_DIR` to that local checkout,
  then rebuild the index.

Generated code is a starting point: review it, configure secrets and infrastructure,
and run its tests/security checks before deploying to production.

See [README.md](README.md) for configuration and details.
