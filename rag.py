from tenacity import retry, stop_after_attempt, wait_exponential
import hashlib
import json
import math
import os
import re
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
GEMINI_MODEL = "models/gemini-3.6-flash"
DEFAULT_K = 12

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
    """Create the Gemini client using the PowerShell environment variable."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Restart PowerShell and set your Gemini key."
        )

    return genai.Client(api_key=api_key)


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


def make_cache_key(question, vectorstore_path):
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
        f"{GEMINI_MODEL}|{EMBEDDING_MODEL}|"
        f"{index_version}|{normalized_question}"
    )

    return hashlib.sha256(cache_input.encode("utf-8")).hexdigest()


def format_context(documents):
    """Format retrieved PHP chunks for Gemini."""
    sections = []

    for number, document in enumerate(documents, start=1):
        source = document.metadata.get("source", "Unknown PHP file")

        sections.append(
            f"--- PHP source {number}: {source} ---\n"
            f"{document.page_content}"
        )

    return "\n\n".join(sections)


def build_prompt(question, context):
    """Create the Gemini prompt with support for informational answers or PHP code generation."""
    return f"""
You are an expert Senior PHP Developer, Software Architect and Code Reviewer.

Your responsibilities are:

• Answer questions about the supplied PHP project.
• Explain code clearly.
• Generate production-ready PHP code when requested.
• Never hallucinate project details.
• Use only the retrieved project context unless the user explicitly asks for new code.
• Mention source files whenever possible.
PHP PROJECT CONTEXT:
{context}

USER REQUEST / QUESTION:
{question}
"""

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
)

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

def generate_answer(client, prompt, media_bytes=None, mime_type=None):
    """
    Generate an answer using Gemini, supporting optional multimodal inputs (image, video, text).
    """
    models = [

    # Primary model
    "models/gemini-3.6-flash",

    # Fallback model
    "models/gemini-3.5-flash",

    ]
    contents = [prompt]
    if media_bytes and mime_type:
        contents.append(
            types.Part.from_bytes(
                data=media_bytes,
                mime_type=mime_type,
            )
        )

    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1500,
                ),
            )

            return (response.text or "").strip()

        except ClientError as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                print(f"{model} is busy. Trying next model...")
                continue
            raise

    raise RuntimeError(
        "All Gemini models are temporarily unavailable."
    )


def save_generated_php_code(answer):
    """Extracts PHP code blocks from the answer and saves them to a file for downloading."""
    php_match = re.search(r"```php\s+(.*?)```", answer, re.DOTALL)
    if not php_match:
        return None
    
    code_content = php_match.group(1).strip()
    generated_dir = PROJECT_DIR / "generated_outputs"
    generated_dir.mkdir(exist_ok=True)
    
    file_path = generated_dir / "generated_solution.php"
    file_path.write_text(code_content, encoding="utf-8")
    return str(file_path)

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

    rules = [

        # --------------------------------------------
        # Greetings
        # --------------------------------------------

        {
            "keywords": ["hello", "hi", "hey"],
            "answer": "Hello! How can I help you with your PHP project today?"
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
        # Project
        # --------------------------------------------

        {
            "keywords": ["project"],
            "answer": "This project is a PHP RAG Assistant built using Gemini 3.6 Flash, FAISS and HuggingFace Embeddings."
        },

        {
            "keywords": ["php"],
            "answer": "The project is developed in PHP."
        },

        {
            "keywords": ["laravel"],
            "answer": "This assistant is designed to understand Laravel/PHP projects."
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
            "answer": "Gemini 3.6 Flash is used as the Large Language Model."
        },

        {
            "keywords": ["llm"],
            "answer": "Gemini 3.6 Flash is the Large Language Model used by this assistant."
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

        # --------------------------------------------
        # Laravel Structure
        # --------------------------------------------

        {
            "keywords": ["database", "mysql"],
            "answer": "Database configuration is available inside config/database.php."
        },

        {
            "keywords": ["route", "routes"],
            "answer": "Application routes are defined in routes/web.php."
        },

        {
            "keywords": ["controller", "controllers"],
            "answer": "Controllers are located inside app/Http/Controllers."
        },

        {
            "keywords": ["model", "models"],
            "answer": "Models are stored inside app/Models."
        },

        {
            "keywords": ["middleware"],
            "answer": "Middleware classes are located inside app/Http/Middleware."
        },

        {
            "keywords": ["migration", "migrations"],
            "answer": "Database migrations are stored in database/migrations."
        },

        {
            "keywords": ["blade", "view", "views"],
            "answer": "Blade templates are located in resources/views."
        },

        {
            "keywords": ["config"],
            "answer": "Configuration files are stored inside the config directory."
        },

        {
            "keywords": ["composer"],
            "answer": "Composer manages PHP dependencies using composer.json."
        },

        # --------------------------------------------
        # Common Modules
        # --------------------------------------------

        {
            "keywords": ["login", "signin", "authentication"],
            "answer": "Authentication is handled through Laravel authentication controllers and middleware."
        },

        {
            "keywords": ["logout"],
            "answer": "Logout functionality is handled through the authentication module."
        },

        {
            "keywords": ["invoice", "billing"],
            "answer": "Invoice functionality is implemented in the invoice module."
        },

        {
            "keywords": ["payment"],
            "answer": "Payment functionality is implemented in the payment module."
        },

        {
            "keywords": ["user", "users"],
            "answer": "User functionality is managed using the User model and related controllers."
        },

        {
            "keywords": ["api"],
            "answer": "API routes are generally defined in routes/api.php."
        }

    ]

    for rule in rules:

        for keyword in rule["keywords"]:

            if keyword in question:

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
    Query the PHP RAG Assistant.

    Pipeline:
    1. Rule Engine
    2. Cache
    3. FAISS Retrieval
    4. Gemini
    5. Save Cache
    """

    vectorstore = rag_components["vectorstore"]
    vectorstore_path = rag_components["vectorstore_path"]
    mock_mode = rag_components["mock_mode"]
    k = rag_components["k"]

    # ============================================================
    # 1. Rule Engine
    # ============================================================

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
    # 2. Cache
    # ============================================================

    cache_key = make_cache_key(
        (question or "") + str(mime_type),
        vectorstore_path,
    )

    if use_cache and not mock_mode and not media_bytes:

        cache = load_answer_cache()

        cached_item = cache.get(cache_key)

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
    # Demo Mode
    # ============================================================

    if mock_mode:

        answer = (
            "Demo Mode is enabled. "
            "Gemini was not contacted."
        )

        return (
            answer,
            source_files,
            documents,
            False,
            None,
        )

    # ============================================================
    # No documents found
    # ============================================================

    if not documents:

        return (
            "I couldn't find this information in the PHP project.",
            [],
            [],
            False,
            None,
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
            media_bytes=media_bytes,
            mime_type=mime_type,
        )

        if not answer.strip():
            answer = "I couldn't generate an answer."

    except Exception as error:

        error_message = str(error)

        if (
            "RESOURCE_EXHAUSTED" in error_message
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
            "model": GEMINI_MODEL,
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
    # ------------------------------------------------------------
    # Build prompt
    # ------------------------------------------------------------
prompt = build_prompt(
        question
        if question
        else "Analyze the attached media.",
        format_context(documents),
    )

    # ------------------------------------------------------------
    # Gemini
    # ------------------------------------------------------------
try:

        answer = generate_answer(
            rag_components["client"],
            prompt,
            media_bytes=media_bytes,
            mime_type=mime_type,
        )

        if not answer.strip():
            answer = "I couldn't generate an answer."

except Exception as error:

        error_message = str(error)

        if (
            "RESOURCE_EXHAUSTED" in error_message
            or "429" in error_message
            or "quota" in error_message.lower()
        ):
            raise GeminiQuotaError(
                extract_retry_seconds(error_message)
            ) from error

        raise

    # ------------------------------------------------------------
    # Save generated PHP code
    # ------------------------------------------------------------
        file_path = save_generated_php_code(answer)

    # ------------------------------------------------------------
    # Save cache
    # ------------------------------------------------------------
        if use_cache and not media_bytes:

            cache = load_answer_cache()

        cache[cache_key] = {
    "question": question,
    "answer": answer,
    "model": GEMINI_MODEL,
    "sources": source_files,
         }
    
        save_answer_cache(cache)