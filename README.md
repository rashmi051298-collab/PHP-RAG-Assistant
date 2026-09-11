# 💻 PHP RAG Assistant

A Retrieval-Augmented Generation (RAG) assistant that understands an existing PHP codebase and answers questions using Google Gemini 3.6 Flash.

The assistant indexes your PHP project into a FAISS vector database using HuggingFace embeddings and retrieves the most relevant code before generating an answer with Gemini.

---

# Features

- PHP project understanding
- Google Gemini 3.6 Flash
- FAISS vector database
- HuggingFace BAAI/bge-base-en-v1.5 embeddings
- Smart MMR document retrieval
- Local answer caching
- Streamlit chat interface
- Demo Mode (No Gemini API calls)
- Adjustable retrieval depth
- Automatic vectorstore loading
- Quota error handling
- Fast semantic search
- Hidden retrieval context from UI
- Cross-file reasoning

---

# Tech Stack

Python

Streamlit

Google Gemini 3.6 Flash

FAISS

LangChain

HuggingFace Embeddings

BAAI/bge-base-en-v1.5

---

# Project Structure

```
PHP_RAG_Assistant/

│
├── app.py
├── ingest.py
├── rag.py
├── requirements.txt
├── README.md
│
├── vectorstore/
│     index.faiss
│     index.pkl
│
├── PHP Files/
│     LoginController.php
│     User.php
│     ...
│
└── answer_cache.json
```

---

# Installation

Clone the repository

```bash
git clone <repository-url>

cd PHP_RAG_Assistant
```

Create virtual environment

```bash
python -m venv venv
```

Activate

Windows

```bash
venv\Scripts\activate
```

Linux / Mac

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# Configure Gemini

Create an API Key from

https://aistudio.google.com/app/apikey

Set the environment variable.

PowerShell

```powershell
$env:GEMINI_API_KEY="YOUR_API_KEY"
```

Command Prompt

```cmd
set GEMINI_API_KEY=YOUR_API_KEY
```

Linux

```bash
export GEMINI_API_KEY="YOUR_API_KEY"
```

---

# Build Vector Database

Place your PHP project inside

```
PHP Files/
```

Run

```bash
python ingest.py
```

Output

```
Reading PHP files...

Creating embeddings...

Saving FAISS vectorstore...

Done.
```

---

# Run Application

```bash
streamlit run app.py
```

---

# How it Works

1. Reads all PHP files

2. Splits them into semantic chunks

3. Generates embeddings

4. Stores vectors inside FAISS

5. User asks a question

6. Relevant PHP code is retrieved

7. Gemini receives only the relevant code

8. Gemini generates the answer

9. Answer is cached locally

---

# Example Questions

Explain LoginController

How does authentication work?

Where is the database connection configured?

Explain this middleware.

Which controller handles user login?

Where is password validation performed?

Which model stores users?

Explain the project architecture.

---

# Demo Mode

Demo Mode allows testing the UI without calling Gemini.

Features

- No API usage
- No quota consumption
- Retrieves PHP code
- Returns sample response

Useful for testing.

---

# Local Answer Cache

Repeated questions reuse previously generated answers.

Benefits

- Faster responses
- Lower Gemini usage
- Reduced API cost
- Better user experience

The cache is stored in

```
answer_cache.json
```

You can clear it directly from the Streamlit interface.

---

# Retrieval

Uses

Maximum Marginal Relevance (MMR)

Benefits

- Better diversity
- Less duplicate chunks
- More accurate context
- Better cross-file reasoning

---

# Adjustable Retrieval

The sidebar lets you choose

```
Code sections to search
```

Higher values

- Better for large projects
- Better for architecture questions

Lower values

- Faster
- Lower token usage

---

# Hidden Context

The application hides

- Retrieved chunks
- Source files
- Internal prompts

Users only see the final answer.

---

# Error Handling

Handles

Missing vectorstore

Missing API key

Gemini quota exceeded

Invalid API key

No relevant PHP code found

Automatic retry messages

---

# Supported PHP Projects

Laravel

CodeIgniter

Core PHP

Symfony

Yii

Custom MVC

Any PHP project

---

# Performance Tips

Use BAAI/bge-base-en-v1.5 embeddings.

Rebuild the vectorstore whenever the PHP project changes.

Keep cached answers enabled for repeated questions.

Increase retrieval count for large codebases.

---

# Future Improvements

Conversation memory

Hybrid retrieval

Code highlighting

Clickable source references

Multi-language support

Project summarization

File-level navigation

Streaming responses

---

# Requirements

Python 3.10+

Google Gemini API Key

Internet connection

---

# License

MIT License