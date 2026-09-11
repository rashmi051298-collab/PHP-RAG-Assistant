# 🚀 PHP RAG Assistant - Quick Start Guide

## ⚡ 5-Minute Setup

### 1️⃣ Initialize Project (Windows)

```bash
# Run setup script
python setup.py

# Activate virtual environment
venv\Scripts\activate

# Verify you see (venv) in your terminal
```

### 1️⃣ Initialize Project (macOS/Linux)

```bash
# Run setup script
python3 setup.py

# Activate virtual environment
source venv/bin/activate

# Verify you see (venv) in your terminal
```

### 2️⃣ Add Your PHP Files

Copy your Laravel/PHP files to:
```
data/laravel-crm-2.2/
├── app/
├── routes/
├── config/
└── ... (all your PHP files)
```

### 3️⃣ Create Vector Store (5-15 minutes)

```bash
# Make sure venv is activated first!
python ingest.py
```

You should see:
```
=== Starting Data Ingestion ===

Total PHP files found: 150
Documents loaded: 150
LangChain documents created: 150
Documents split into 450 chunks
Vector store saved successfully to vectorstore

=== Data Ingestion Complete ===
```

### 4️⃣ Launch the App

```bash
# Make sure venv is activated!
streamlit run app.py
```

This opens `http://localhost:8501` in your browser automatically.

### 5️⃣ Start Chatting! 💬

In the Streamlit interface:
1. Click **"Initialize RAG System"** button
2. Ask questions like:
   - "What does the LoginController do?"
   - "Explain the authentication flow"
   - "Show me the API routes"

---

## 📁 Project Structure After Setup

```
PHP_RAG_Assistant/
├── venv/                    ← Virtual environment (created by setup.py)
├── data/
│   └── laravel-crm-2.2/     ← Your PHP files go here
├── vectorstore/             ← Created by ingest.py (index + metadata)
│   ├── index.faiss
│   └── index.pkl
├── app.py                   ← Streamlit chat interface
├── ingest.py                ← Data ingestion script
├── rag.py                   ← RAG chain setup
├── setup.py                 ← Automated setup
├── requirements.txt         ← Dependencies
├── README.md                ← Full documentation
├── QUICKSTART.md            ← This file
└── .gitignore               ← Git configuration
```

---

## 🆘 Common Issues & Solutions

### ❌ "Command not found: python"
**Solution**: Use `python3` instead on macOS/Linux
```bash
python3 setup.py
python3 ingest.py
streamlit run app.py
```

### ❌ "No module named 'streamlit'"
**Solution**: Make sure virtual environment is activated
```bash
# Check (venv) appears in terminal
# If not, run:
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

### ❌ "Vectorstore not found"
**Solution**: Run data ingestion first
```bash
python ingest.py
```

### ❌ "Out of Memory"
**Solution**: Your code is too large. Options:
1. Process in smaller batches
2. Use `chunk_size=250` in ingest.py
3. Reduce `max_new_tokens` in rag.py

### ❌ "CUDA not available"
**Solution**: This is fine - will use CPU. Or install GPU support:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## 🎯 Workflow Summary

```
1. Setup: python setup.py
2. Add Files: Copy to data/laravel-crm-2.2/
3. Ingest: python ingest.py
4. Run: streamlit run app.py
5. Chat: Use web interface
```

---

## ⚙️ Configuration

### Change Data Location
Edit line in `ingest.py`:
```python
data_dir = r"D:\PHP_RAG_Assistant\PHP Files"  # Change this path
```

### Change LLM Model
Edit line in `app.py` sidebar or in `rag.py`:
```python
model_name = "google/gemma-2-2b-it"  # Default
# Try: "meta-llama/Llama-2-7b-chat-hf"
```

### Adjust Retrieval
In `app.py` sidebar:
- **Number of documents**: 1-10 (default: 4)
- Lower = faster, less context
- Higher = slower, more context

---

## 📊 Performance Expectations

| Hardware | Setup Time | Ingest (100 files) | First Query | Subsequent |
|----------|-----------|-------------------|-------------|------------|
| CPU only | 5 min | 15 min | 45 sec | 15 sec |
| GPU (6GB) | 5 min | 3 min | 8 sec | 3 sec |

---

## 🔗 Next Steps

- 📚 Read [README.md](README.md) for advanced configuration
- 🎓 Check example questions in the app
- 🤖 Try different LLM models
- 📈 Scale to larger codebases

---

## 💡 Tips

1. **First Run Slow?** Yes, model loading takes time. Subsequent queries are fast.
2. **Want Faster?** Use a GPU or reduce `chunk_size` in ingest.py
3. **Too Many Results?** Reduce `k` value in app.py sidebar
4. **Bad Answers?** Add more context by increasing `k`

---

## 🆘 Need More Help?

1. Check README.md → Troubleshooting section
2. Read the docstrings in app.py, ingest.py, rag.py
3. Check Streamlit docs: https://docs.streamlit.io

---

**Happy coding! 🎉** If you have questions, check the full documentation in README.md
