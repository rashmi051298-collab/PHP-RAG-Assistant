from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
import hashlib
import json
import math
import os
import re
import requests
import zipfile
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath
from google import genai
from google.genai import types
from google.genai.errors import APIError, ServerError
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
GEMINI_MODEL_RANGE = "2.5-3.8"
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
ANSWER_VERSION = "php-vibe-coding-v2"
DEFAULT_K = 12
MAX_PROJECT_FILES = 50
MAX_PROJECT_FILE_BYTES = 512 * 1024
MAX_PROJECT_TOTAL_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_TOKENS = 8192

ASSISTANT_IMPLEMENTATION_CONTEXT = """
This PHP Vibe Coding Assistant is a Python application with a Streamlit chat
UI (app.py). ingest.py reads supported text and documentation files from the
configured knowledge base, splits them into 1,400-character chunks with 250-character
overlap, creates normalized embeddings with Hugging Face's BAAI/bge-base-en-v1.5
model, and saves a LangChain FAISS vectorstore under vectorstore/. At query time,
rag.py retrieves relevant repository chunks with FAISS maximum marginal relevance
(MMR). Code-generation requests use available Gemini text models; explanations use
NVIDIA NIM. The app supports local answer caching, optional image/video input, Demo
Mode, and downloading generated PHP files or multi-file projects.
Questions about the assistant itself should use these implementation details;
questions about the indexed repository should use retrieved file context.
"""

PROJECT_OVERVIEW_ANSWER = """\
## How this PHP Vibe Coding Assistant is built

- **Python and Streamlit** provide the application logic and chat interface (`app.py`).
- **Repository ingestion** (`ingest.py`) reads supported text, source-code, and
  documentation files and splits them into 1,400-character chunks with 250-character
  overlap.
- **Hugging Face embeddings** use `BAAI/bge-base-en-v1.5` to represent each chunk as
  a normalized vector.
- **LangChain and FAISS** store those vectors locally in `vectorstore/`. For a question,
  FAISS uses maximum marginal relevance (MMR) to retrieve relevant, varied chunks.
- **Provider routing** sends PHP code/project generation to available Gemini text
  models and explanations to NVIDIA NIM.
- **Code generation** can return a single PHP file or a multi-file project ZIP.
- **Local answer caching** avoids another model request for repeated questions. The app
  also supports Demo Mode and optional image/video input.

The flow is: repository files → chunks → embeddings → FAISS index → question →
relevant context → Gemini for code or NVIDIA for explanations. Questions about the
assistant's own architecture use the implementation details above; repository
questions search the indexed files.
"""

# ============================================================
# Hybrid Rule Engine
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent
CACHE_FILE = PROJECT_DIR / "answer_cache.json"


class GeminiQuotaError(RuntimeError):
    """Raised when Gemini rejects a request because of quota/rate limits."""

    def __init__(self, retry_seconds=None):
        self.retry_seconds = retry_seconds

        if retry_seconds:
            message = (
                f"Gemini quota is temporarily unavailable. "
                f"Please wait about {retry_seconds} seconds and try again."
            )
        else:
            message = (
                "Gemini quota is currently unavailable. "
                "Please wait and try again later."
            )

        super().__init__(message)


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def load_vectorstore(vectorstore_path="vectorstore"):
    """Load the FAISS vectorstore created by ingest.py."""
    vectorstore_dir = Path(vectorstore_path)

    if not vectorstore_dir.exists():
        raise FileNotFoundError(
            "Vectorstore not found. Please run: python ingest.py"
        )

    return FAISS.load_local(
        str(vectorstore_dir),
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )


def load_gemini_client():
    """Create the Gemini client when a key is configured."""
    api_key = os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key) if api_key else None


def load_answer_cache():
    """Read locally cached answers."""
    if not CACHE_FILE.exists():
        return {}

    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_answer_cache(cache):
    """Save answers locally for reuse."""
    temporary_file = CACHE_FILE.with_suffix(".tmp")

    temporary_file.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    temporary_file.replace(CACHE_FILE)


def clear_answer_cache():
    """Delete all locally saved answers."""
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()


def make_cache_key(question, vectorstore_path, provider="gemini"):
    """
    Create a cache key based on the question, model, and current FAISS index.
    Rebuilding the vectorstore automatically makes old cached answers unused.
    """
    index_file = Path(vectorstore_path) / "index.faiss"

    if index_file.exists():
        index_version = str(index_file.stat().st_mtime_ns)
    else:
        index_version = "no-index"

    normalized_question = " ".join(question.lower().split())

    cache_input = (
        f"{ANSWER_VERSION}|{provider}|{GEMINI_MODEL_RANGE}|{NVIDIA_MODEL}|"
        f"{EMBEDDING_MODEL}|"
        f"{index_version}|{normalized_question}"
    )

    return hashlib.sha256(cache_input.encode("utf-8")).hexdigest()


def format_context(documents):
    """Format retrieved repository chunks for the selected language model."""
    sections = []

    for number, document in enumerate(documents, start=1):
        source = document.metadata.get("source", "Unknown repository file")

        sections.append(
            f"--- Repository source {number}: {source} ---\n"
            f"{document.page_content}"
        )

    return "\n\n".join(sections)


def build_prompt(question, context):
    """Create the provider-neutral prompt for questions and PHP project generation."""
    return f"""
You are a senior PHP engineer, software architect, and technical documentation assistant.

Your responsibilities are:

• Answer questions about the assistant or the supplied repository and its documentation.
• Explain source code and technical material clearly.
• Use retrieved repository context as evidence for repository-specific claims and cite file paths whenever possible.
• If the retrieved context does not answer a repository-specific question, say so instead of inventing project facts.
• You may provide general software engineering guidance, clearly distinguishing it from facts found in the repository.
• Generate maintainable, production-minded PHP code using secure defaults, input validation,
  authorization checks where appropriate, safe database access, and explicit error handling.
• For a request to build a complete project, provide a coherent runnable project, not just
  a sketch. Include appropriate application files, safe configuration examples, database
  changes when needed, tests, and setup/run instructions.
• Do not claim generated code is production-ready or tested unless it has actually been
  reviewed and run. State assumptions and external setup requirements.
• For a single PHP file, provide one fenced `php` code block.
• For a multi-file project, put every file in its own fenced block using this exact header:
  `file path=relative/path/from/project/root`
  Example header: `file path=public/index.php`
  Never use absolute paths or `..` path segments. Include each file's complete contents.
• Keep project file blocks separate from explanatory prose, and include a concise file
  tree plus instructions for installing, configuring, running, and testing the project.

ASSISTANT IMPLEMENTATION CONTEXT:
{ASSISTANT_IMPLEMENTATION_CONTEXT}

REPOSITORY CONTEXT:
{context}

USER REQUEST / QUESTION:
{question}
"""

def extract_retry_seconds(error_message):
    """
    Extract Gemini retry delay from the error message.
    """

    match = re.search(
        r"retry(?:\s+in)?\s+(\d+(?:\.\d+)?)s",
        error_message,
        flags=re.IGNORECASE,
    )

    if match:
        return math.ceil(float(match.group(1)))

    return None


def is_code_generation_request(question):
    """Identify requests that ask the assistant to create or change code."""
    question = question or ""
    starts_with_explanation = re.match(
        r"\s*(?:explain|describe|tell me|what|how|why|where|when|"
        r"compare|summarize|review)\b",
        question,
        flags=re.IGNORECASE,
    )
    explicit_code_action = re.search(
        r"\b(?:generate|write|create|implement|scaffold|refactor|fix|"
        r"debug|modify|update|add|convert)\b"
        r".{0,100}\b(?:php|code|class|function|file|website|web\s+app|"
        r"application|project|api|script|feature|module|endpoint|site|"
        r"bug|error|issue)\b",
        question,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if starts_with_explanation and not explicit_code_action:
        return False
    if starts_with_explanation:
        return bool(
            re.search(
                r"\b(?:and|then)\s+(?:please\s+)?"
                r"(?:generate|write|create|implement|scaffold|refactor|"
                r"fix|debug|modify|update|add|convert|make|build)\b",
                question,
                flags=re.IGNORECASE,
            )
        )

    return bool(
        re.search(
            r"\b(?:generate|write|create|build|implement|scaffold|"
            r"refactor|fix|debug|modify|update|add|convert|make)\b"
            r".{0,100}\b(?:php|code|class|function|file|website|web\s+app|"
            r"application|project|api|script|feature|module|endpoint|"
            r"site|bug|error|issue)\b"
            r"|\b(?:show|give|provide)\s+(?:me\s+)?"
            r"(?:the\s+)?(?:php\s+)?(?:code|function|class|script|project|app)\b"
            r"|\bcode\s+for\s+(?:a|an|the|my)\b"
            r"|\b(?:i|we)\s+(?:want|need)\s+(?:you\s+to\s+)?"
            r"(?:a|an|the)?\s*(?:php\s+)?"
            r"(?:app|application|project|website|site|api|script|"
            r"feature|module)\b",
            question,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )


def get_supported_gemini_models(client):
    """List available text-generation models from Gemini 2.5 through 3.8."""
    models = []
    for model in client.models.list(
        config=types.ListModelsConfig(page_size=1000)
    ):
        name = model.name or ""
        model_id = name.removeprefix("models/")
        version_match = re.match(
            r"^gemini-(2\.5|3\.([0-8]))(?:-|$)",
            model_id,
            flags=re.IGNORECASE,
        )
        supported_actions = {
            action.lower() for action in (model.supported_actions or [])
        }
        if not version_match or "generatecontent" not in supported_actions:
            continue

        if re.search(
            r"(?:^|-)(?:image|live|tts|transcribe|embedding|aqa)(?:-|$)",
            model_id,
            flags=re.IGNORECASE,
        ):
            continue
        models.append((version_match, model_id, name))

    def sort_key(item):
        match, model_id, _ = item
        family = match.group(1)
        major, minor = (2, 5) if family == "2.5" else (3, int(match.group(2)))
        model_variant = model_id.lower()
        if "pro" in model_variant:
            priority = 3
        elif "lite" in model_variant:
            priority = 1
        else:
            priority = 2
        return major, minor, priority, model_id

    return [name for _, _, name in sorted(models, key=sort_key, reverse=True)]


def generate_gemini_answer(client, prompt, media_bytes=None, mime_type=None):
    """Try currently available Gemini text-generation models in descending order."""
    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to use Gemini for code generation."
        )

    models = get_supported_gemini_models(client)
    if not models:
        raise RuntimeError(
            "No Gemini 2.5–3.8 text-generation models are available for this API key."
        )

    contents = [prompt]
    if media_bytes and mime_type:
        contents.append(
            types.Part.from_bytes(
                data=media_bytes,
                mime_type=mime_type,
            )
        )

    last_error = None
    for model in models:
        try:
            response = _generate_content_with_retry(client, model, contents)
            answer = (response.text or "").strip()
            if answer:
                return answer
            last_error = RuntimeError(f"{model} returned an empty response.")
        except APIError as error:
            if error.code not in {404, 429, 500, 502, 503, 504}:
                raise
            last_error = error
            print(f"{model} is unavailable (HTTP {error.code}); trying next Gemini model.")

    raise RuntimeError(
        "All available Gemini text-generation models from 2.5 through 3.8 "
        "are currently unavailable."
    ) from last_error


def generate_nvidia_answer(prompt, media_bytes=None):
    """Generate a text explanation with NVIDIA's OpenAI-compatible NIM API."""
    if media_bytes:
        raise RuntimeError(
            f"The configured NVIDIA model ({NVIDIA_MODEL}) accepts text prompts only. "
            "Remove the attachment or configure a multimodal NVIDIA model."
        )

    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "NVIDIA_API_KEY is not set. Add it to use NVIDIA for explanations."
        )

    try:
        response = requests.post(
            NVIDIA_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": NVIDIA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 2048,
                "chat_template_kwargs": {"enable_thinking": False},
                "stream": False,
            },
            timeout=(10, 300),
        )
        response.raise_for_status()
    except requests.RequestException as error:
        status_code = (
            error.response.status_code
            if isinstance(error, requests.HTTPError) and error.response is not None
            else None
        )
        message = (
            "NVIDIA explanation request failed"
            + (f" with HTTP {status_code}" if status_code else "")
        )
        error_detail = " ".join(str(error).split())[:300]
        error_detail = re.sub(
            r"(?i)\bBearer\s+\S+",
            "Bearer [redacted]",
            error_detail,
        )
        error_detail = re.sub(
            r"(?i)(https?://)[^/@\s]+@",
            r"\1[redacted]@",
            error_detail,
        )
        if error_detail:
            message += f" ({type(error).__name__}: {error_detail})"

        if status_code == 410:
            message += (
                f" (Gone) for model {NVIDIA_MODEL}. That model or its hosted "
                "inference service may have been retired. Select a currently "
                "available model from NVIDIA's API Catalog and set NVIDIA_MODEL."
            )
        else:
            message += ". Check NVIDIA_API_KEY, NVIDIA_MODEL, and API availability."

        if isinstance(error, requests.HTTPError) and error.response is not None:
            try:
                error_payload = error.response.json()
            except ValueError:
                error_payload = error.response.text
            if isinstance(error_payload, dict):
                error_detail = error_payload.get("detail") or error_payload.get("error")
                if isinstance(error_detail, dict):
                    error_detail = (
                        error_detail.get("message")
                        or error_detail.get("detail")
                        or error_detail.get("title")
                    )
            else:
                error_detail = error_payload

            if error_detail:
                safe_detail = " ".join(str(error_detail).split())[:500]
                message += f" NVIDIA response: {safe_detail}"

        raise RuntimeError(message) from error

    try:
        answer = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise RuntimeError(
            "NVIDIA returned an unexpected chat-completions response."
        ) from error

    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("NVIDIA returned an empty explanation.")
    return answer.strip()


@retry(
    retry=retry_if_exception_type(ServerError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    reraise=True,
)
def _generate_content_with_retry(client, model, contents):
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ),
    )


def generate_answer(
    client,
    prompt,
    question,
    media_bytes=None,
    mime_type=None,
):
    """Route code-generation requests to Gemini and explanations to NVIDIA."""
    if is_code_generation_request(question):
        return generate_gemini_answer(
            client,
            prompt,
            media_bytes=media_bytes,
            mime_type=mime_type,
        )
    return generate_nvidia_answer(
        prompt,
        media_bytes=media_bytes,
    )


def _extract_generated_project_files(answer):
    """Extract and validate path-labeled file blocks from a generated project."""
    project_files = {}
    code_blocks = re.finditer(
        r"```([^\r\n`]*)\r?\n(.*?)```",
        answer,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for code_match in code_blocks:
        header = code_match.group(1).strip()
        path_match = re.fullmatch(
            r"(?:file\s+)?(?:path|file)\s*=\s*(.+)",
            header,
            flags=re.IGNORECASE,
        )
        if not path_match:
            continue

        relative_path = path_match.group(1).strip().strip("\"'")
        posix_path = PurePosixPath(relative_path.replace("\\", "/"))
        windows_path = PureWindowsPath(relative_path)
        if (
            not relative_path
            or posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or any(part in {"", ".", ".."} for part in posix_path.parts)
        ):
            raise ValueError(
                f"Generated project contains an unsafe file path: {relative_path!r}"
            )

        normalized_path = posix_path.as_posix()
        if normalized_path in project_files:
            raise ValueError(
                f"Generated project contains a duplicate file path: {normalized_path}"
            )

        content = code_match.group(2).strip()
        content_size = len(content.encode("utf-8"))
        if content_size > MAX_PROJECT_FILE_BYTES:
            raise ValueError(
                f"Generated project file exceeds the "
                f"{MAX_PROJECT_FILE_BYTES // 1024} KiB limit: {normalized_path}"
            )

        project_files[normalized_path] = content
        if len(project_files) > MAX_PROJECT_FILES:
            raise ValueError(
                f"Generated project exceeds the {MAX_PROJECT_FILES}-file limit."
            )

    total_size = sum(
        len(content.encode("utf-8")) for content in project_files.values()
    )
    if total_size > MAX_PROJECT_TOTAL_BYTES:
        raise ValueError(
            "Generated project exceeds the "
            f"{MAX_PROJECT_TOTAL_BYTES // (1024 * 1024)} MiB total size limit."
        )

    return project_files


def save_generated_php_code(answer):
    """Save a generated PHP file or package path-labeled project files as a ZIP."""
    project_files = _extract_generated_project_files(answer)
    generated_dir = PROJECT_DIR / "generated_outputs"
    generated_dir.mkdir(exist_ok=True)

    if project_files:
        archive_path = generated_dir / "generated_php_project.zip"
        with zipfile.ZipFile(
            archive_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for relative_path, content in project_files.items():
                archive.writestr(relative_path, content)
        return str(archive_path)

    code_blocks = re.finditer(
        r"```([^\r\n`]*)\r?\n(.*?)```",
        answer,
        flags=re.DOTALL | re.IGNORECASE,
    )
    for code_match in code_blocks:
        language = code_match.group(1).strip().lower()
        candidate = code_match.group(2).strip()
        is_php_code = re.search(
            r"<\?php|\b(class|function|namespace|use|echo|require|include)\b",
            candidate,
        )
        if language == "php" or (not language and is_php_code):
            file_path = generated_dir / "generated_solution.php"
            file_path.write_text(candidate, encoding="utf-8")
            return str(file_path)

    return None

def create_rag_chain(vectorstore_path="vectorstore", k=DEFAULT_K, mock_mode=False):
    """
    Load the RAG components.

    Demo Mode loads only FAISS; Gemini is not contacted and no key is required.
    """
    return {
        "vectorstore": load_vectorstore(vectorstore_path),
        "client": None if mock_mode else load_gemini_client(),
        "k": k,
        "mock_mode": mock_mode,
        "vectorstore_path": vectorstore_path,
    }

def check_rule_engine(question: str):
    """
    Hybrid Rule Engine.

    Returns:
        dict -> if a rule matches
        None -> otherwise
    """

    question = question.lower().strip()

    question = re.sub(r"[^a-z0-9 ]", " ", question)
    question = " ".join(question.split())

    refers_to_assistant = re.search(
        r"\b(?:this|the|our)\s+"
        r"(?:(?:php\s+)?(?:rag\s+)?|repository\s+knowledge\s+|knowledge\s+base\s+)?"
        r"(?:assistant|project|system|application|app)\b"
        r"|\b(?:php rag|repository knowledge|knowledge base) assistant\b",
        question,
    )
    asks_about_build_or_architecture = re.search(
        r"\b(?:overview|architecture|tech stack|technology|technologies|"
        r"components|workflow|pipeline|built|building|developed|designed)\b",
        question,
    )

    if refers_to_assistant and asks_about_build_or_architecture:
        return {
            "matched": True,
            "answer": PROJECT_OVERVIEW_ANSWER,
            "keyword": "project architecture",
        }

    rules = [

        # --------------------------------------------
        # Greetings
        # --------------------------------------------

        {
            "keywords": ["hello", "hi", "hey"],
            "answer": "Hello! How can I help you with your repository today?"
        },

        {
            "keywords": ["good morning"],
            "answer": "Good morning! How can I help you?"
        },

        {
            "keywords": ["good afternoon"],
            "answer": "Good afternoon! How can I help you?"
        },

        {
            "keywords": ["good evening"],
            "answer": "Good evening! How can I help you?"
        },

        {
            "keywords": ["thanks", "thank you"],
            "answer": "You're welcome!"
        },

        {
            "keywords": ["bye", "goodbye"],
            "answer": "Goodbye! Have a great day."
        },

        # --------------------------------------------
        # AI
        # --------------------------------------------

        {
            "keywords": ["rag"],
            "answer": "This project uses Retrieval-Augmented Generation (RAG)."
        },

        {
            "keywords": ["gemini"],
            "answer": "PHP code and project generation use available Gemini text models from versions 2.5 through 3.8."
        },

        {
            "keywords": ["llm"],
            "answer": "PHP code generation uses Gemini; explanations use NVIDIA NIM."
        },

        {
            "keywords": ["embedding", "embeddings"],
            "answer": "Embeddings are generated using BAAI/bge-base-en-v1.5."
        },

        {
            "keywords": ["faiss", "vector", "vectorstore"],
            "answer": "FAISS is used as the vector database."
        },

        {
            "keywords": ["cache"],
            "answer": "Generated answers are stored in answer_cache.json."
        },

    ]

    for rule in rules:

        for keyword in rule["keywords"]:

            if question == keyword or (
                " " in keyword
                and re.search(rf"\b{re.escape(keyword)}\b", question)
            ):

                return {
                    "matched": True,
                    "answer": rule["answer"],
                    "keyword": keyword
                }

    return None


def query_rag(
    rag_components,
    question,
    use_cache=True,
    media_bytes=None,
    mime_type=None,
):
    """
    Query the repository knowledge assistant.

    Pipeline:
    1. Rule Engine
    2. Cache
    3. FAISS Retrieval
    4. Gemini or NVIDIA, selected by the request type
    5. Save Cache
    """

    vectorstore = rag_components["vectorstore"]
    vectorstore_path = rag_components["vectorstore_path"]
    mock_mode = rag_components["mock_mode"]
    k = rag_components["k"]
    provider = (
        "gemini"
        if is_code_generation_request(question)
        else "nvidia"
    )

    # ============================================================
    # 2. Cache
    # ============================================================

    cache_key = make_cache_key(
        (question or "") + str(mime_type),
        vectorstore_path,
        provider,
    )

    if mock_mode or (use_cache and not media_bytes):

        cache = load_answer_cache()

        cached_item = cache.get(cache_key)

        if cached_item is None and question:
            normalized_question = " ".join(question.lower().split())
            cached_item = next(
                (
                    item
                    for item in cache.values()
                    if item.get("answer_version") == ANSWER_VERSION
                    and item.get("provider") == provider
                    and " ".join(item.get("question", "").lower().split())
                    == normalized_question
                ),
                None,
            )

        if cached_item:

            file_path = save_generated_php_code(
                cached_item["answer"]
            )

            return (
                cached_item["answer"],
                cached_item.get("sources", []),
                [],
                True,
                file_path,
            )

    if mock_mode:
        return (
            "Demo Mode is enabled. Gemini was not contacted.",
            [],
            [],
            False,
            None,
        )

    rule = check_rule_engine(question or "")

    if rule:
        return (
            rule["answer"],
            ["Rule Engine"],
            [],
            False,
            None,
        )

    # ============================================================
    # 3. Retrieve Documents
    # ============================================================

    documents = vectorstore.max_marginal_relevance_search(
        question,
        k=k,
        fetch_k=max(40, k * 4),
        lambda_mult=0.6,
    )

    source_files = list(
        dict.fromkeys(
            doc.metadata.get("source", "Unknown")
            for doc in documents
        )
    )

    # ============================================================
    # 4. Build Prompt
    # ============================================================

    prompt = build_prompt(
        question if question else "Analyze the attached media.",
        format_context(documents),
    )

    # ============================================================
    # 5. Gemini
    # ============================================================

    try:

        answer = generate_answer(
            rag_components["client"],
            prompt,
            question=question or "",
            media_bytes=media_bytes,
            mime_type=mime_type,
        )

        if not answer.strip():
            answer = "I couldn't generate an answer."

    except Exception as error:

        error_message = str(error)

        has_gemini_rate_limit_cause = False
        cause = error
        while cause is not None:
            if isinstance(cause, APIError) and cause.code == 429:
                has_gemini_rate_limit_cause = True
                break
            cause = cause.__cause__

        if provider == "gemini" and (
            has_gemini_rate_limit_cause
            or "RESOURCE_EXHAUSTED" in error_message
            or "429" in error_message
            or "quota" in error_message.lower()
        ):
            raise GeminiQuotaError(
                extract_retry_seconds(error_message)
            ) from error

        raise

    # ============================================================
    # Save Generated PHP File
    # ============================================================

    file_path = save_generated_php_code(answer)

    # ============================================================
    # Save Cache
    # ============================================================

    if use_cache and not media_bytes:

        cache = load_answer_cache()

        cache[cache_key] = {
            "question": question,
            "answer": answer,
            "answer_version": ANSWER_VERSION,
            "provider": provider,
            "model": GEMINI_MODEL_RANGE if provider == "gemini" else NVIDIA_MODEL,
            "sources": source_files,
        }

        save_answer_cache(cache)

    # ============================================================
    # Return
    # ============================================================

    return (
        answer,
        source_files,
        documents,
        False,
        file_path,
    )