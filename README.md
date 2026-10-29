# PHP Vibe Coding Assistant

Ask PHP questions, generate PHP code, and request complete multi-file PHP projects
from a Streamlit chat interface. The assistant can use the current local repository
as RAG context and package generated project files into a ZIP for download.

## Technology

- **Vector database:** FAISS
- **LLM:** Google Gemini Flash, accessed with `google-genai`
- **Explanation model:** NVIDIA NIM `nvidia/nemotron-3.5-lightning-30b-a3b`
- **Embedding model:** Hugging Face `BAAI/bge-base-en-v1.5`
- **Application:** Python, LangChain, and Streamlit

The RAG flow remains: repository files → overlapping text chunks → Hugging Face
embeddings → local FAISS index → retrieved context → model selected by request type.

## Setup

1. Install Python 3.10 or later and create a virtual environment:

   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

   On macOS/Linux, activate with `source venv/bin/activate`.

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure a Gemini API key:

   ```powershell
   $env:GEMINI_API_KEY="YOUR_API_KEY"
   $env:NVIDIA_API_KEY="YOUR_NVIDIA_API_KEY"
   ```

   Code-generation requests use Gemini; explanation requests use NVIDIA. Set both
   keys in the environment where Streamlit is started. On macOS/Linux, use
   `export GEMINI_API_KEY="YOUR_API_KEY"` and
   `export NVIDIA_API_KEY="YOUR_NVIDIA_API_KEY"`.

## Model routing

- PHP code generation, changes, and complete project requests go to Gemini. The
  assistant discovers available Gemini models that support text generation, from
  versions 2.5 through 3.8, and tries them newest-first when a model is unavailable
  or the service is temporarily rate-limited.
- Explanation and other non-code questions go to NVIDIA NIM using
  `nvidia/nemotron-3.5-lightning-30b-a3b` by default. Override the NVIDIA model with
  `NVIDIA_MODEL`.
- If NVIDIA returns HTTP 410, the app reports the configured model and provider
  response detail. Choose a currently available text-generation model from
  NVIDIA's API Catalog, set `NVIDIA_MODEL` to its exact ID, then restart Streamlit.
- NVIDIA's configured model is text-only. Image/video prompts need a multimodal
  NVIDIA model to be configured; otherwise the assistant reports that limitation.
- Set up NVIDIA credentials at [build.nvidia.com](https://build.nvidia.com/).

## Knowledge base

By default, ingestion indexes this local `PHP-RAG-Assistant` repository directly;
there is no need to clone or copy it into a second folder. It reads supported
text-based source, configuration, and documentation files, including common
programming-language files plus Markdown, reStructuredText, JSON, YAML, TOML, and
plain text. Relative paths are retained as source metadata. Binary files and common
generated/dependency directories are skipped, as is the legacy `data/` directory.
`.env` files other than `.env.example` are excluded.

To index a different local repository instead, set `KNOWLEDGE_BASE_DIR` before
ingestion. Relative paths are resolved from the assistant project directory.

PowerShell:

```powershell
$env:KNOWLEDGE_BASE_DIR="D:\path\to\your\repository"
```

macOS/Linux:

```bash
export KNOWLEDGE_BASE_DIR="/path/to/your/repository"
```

Build or refresh the FAISS index whenever the repository changes:

```bash
python ingest.py
```

The index is saved under `vectorstore/`. The GitHub repository being indexed must
already be available locally. When the app starts and this index is missing (as it
is by default in Streamlit Cloud, where `vectorstore/` is not committed), the app
builds the index automatically. The first launch can take several minutes while
the embedding model is downloaded and the repository is indexed.

## Run the assistant

```bash
streamlit run app.py
```

Ask questions about architecture, implementation, configuration, or documentation.
The assistant retrieves relevant chunks from the index and includes source paths
when responding. If the indexed files do not support a repository-specific answer,
it should say so rather than infer project facts.
After each answer, the chat shows its end-to-end response time. This includes repository
search and, when needed, the remote model response. Provider/network time varies; an
answer served from the local cache does not make a model request. The first launch's
index and embedding-model setup is separate from per-question response time.
Code-generation requests use a best-effort 5-second target and project-generation
requests use a 10-second target. These are not hard deadlines: model/network latency
can exceed them. To reduce work before generation, code requests retrieve up to 4
repository chunks and project requests up to 6; available Gemini Flash models are
preferred over Pro models within the same version. Explanations keep the configured
retrieval depth. Single-code responses use a 2,048-token output ceiling to reduce
generation time; project responses keep the existing 8,192-token ceiling to preserve
room for multi-file output.

## Features

- MMR retrieval from a local FAISS vectorstore
- Hugging Face embeddings and Gemini responses
- Repository-aware source paths
- Local answer caching, 10-minute Gemini model-discovery caching, and adjustable
  retrieval depth
- Best-effort 5-second code and 10-second project response targets
- Demo Mode for testing without Gemini calls
- Optional image/video prompts
- Downloadable single PHP files and multi-file project ZIPs

For project requests, describe the desired features, framework/version, database,
authentication, and deployment target when known. Generated projects use
production-minded conventions and can include tests and setup instructions, but
must be reviewed, configured, and tested in your environment before deployment.
The assistant does not execute or certify generated projects.

## Notes

- First-time indexing downloads/loads the Hugging Face embedding model and may take
  several minutes.
- The index should be rebuilt after changing the indexed repository.
- Do not include secrets in a knowledge base. `.env` files are automatically
  excluded, but review repository contents before indexing.
- Generated answers are cached in `answer_cache.json`.

See [QUICKSTART.md](QUICKSTART.md) for a short workflow.
