# 🚀 PHP RAG Assistant

<p align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![PHP](https://img.shields.io/badge/PHP-8.x-777BB4?logo=php)
![Gemini](https://img.shields.io/badge/LLM-Gemini%203.6%20Flash-4285F4)
![FAISS](https://img.shields.io/badge/Vector%20DB-FAISS-green)
![LangChain](https://img.shields.io/badge/LangChain-RAG-success)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-yellow)

</p>

AI-powered assistant...

## 🏗️ System Architecture

```mermaid
flowchart TD

A[👤 User]

B[💻 Streamlit UI]

C[🧠 Hybrid Rule Engine]

D[📚 FAISS Vector Database]

E[🔎 Semantic Retrieval]

F[📄 Retrieved PHP Context]

G[🤖 Gemini 3.6 Flash]

H[💬 AI Response]

I[(Answer Cache)]

A --> B
B --> C

C -->|Rule Match| H
C -->|No Rule Match| D

D --> E
E --> F
F --> G
G --> H

H --> I
```
