import os
import json
from pathlib import Path

from rag import (
    create_rag_chain,
    query_rag,
    load_answer_cache,
    clear_answer_cache,
)
import streamlit as st

VECTORSTORE_PATH = "vectorstore"
DEFAULT_K = 12


def init_session_state():
    """Create session variables when the app first opens."""
    if "rag_components" not in st.session_state:
        st.session_state.rag_components = None

    if "messages" not in st.session_state:
        st.session_state.messages = []


def load_rag_system(k, mock_mode):
    """Load FAISS and, unless in Demo Mode, the Gemini client."""
    with st.spinner("Loading the PHP assistant..."):
        st.session_state.rag_components = create_rag_chain(
            vectorstore_path=VECTORSTORE_PATH,
            k=k,
            mock_mode=mock_mode,
        )


def display_chat_history():
    """Show previous chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def main():
    st.set_page_config(
        page_title="PHP RAG Assistant",
        page_icon="💻",
        layout="wide",
    )

    init_session_state()

    st.title("💬 PHP RAG Assistant")
    st.caption("Ask questions about your PHP project, upload multimodal prompts, and download generated PHP files.")

    # Move all controls and settings into the sidebar to keep the chat front and center
    with st.sidebar:
        st.subheader("Controls")

        k = st.slider(
            "Code sections to search",
            min_value=4,
            max_value=12,
            value=DEFAULT_K,
            help="More sections help with questions involving multiple files.",
        )

        mock_mode = st.checkbox(
            "Demo Mode",
            value=False,
            help="Test the interface without calling Gemini or using API quota.",
        )

        use_cache = st.checkbox(
            "Use saved answers",
            value=True,
            disabled=mock_mode,
            help="Repeated questions reuse earlier answers and do not call Gemini.",
        )

        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.divider()

        # Saved answers section placed right before the Clear Saved Answers button
        st.subheader("Saved Answers Section")
        cache = load_answer_cache()
        if not cache:
            st.info("No saved answers found.")
        else:
            st.write(f"Total Saved: {len(cache)}")
            for i, item in enumerate(list(cache.values())[-3:], start=1):
                with st.expander(f"Q: {item['question'][:30]}..."):
                    st.write(item["answer"])

        if st.button("🧹 Clear Saved Answers", use_container_width=True):
            clear_answer_cache()
            st.success("Saved answers cleared.")
            st.rerun()

        if st.button("🔄 Reload Assistant", use_container_width=True):
            st.session_state.rag_components = None
            st.rerun()

        st.divider()

        st.subheader("How to Use")
        st.markdown("""
1. Upload image, video, or text prompt (optional).
2. Type your question or request code.
3. Download generated PHP files directly.
""")

        if mock_mode:
            st.info("Demo Mode: Gemini is not used.")
        elif st.session_state.rag_components:
            st.success("✓ Assistant ready")
        else:
            st.warning("Assistant is loading")

    existing_components = st.session_state.rag_components

    # Reload automatically if retrieval count or mode was changed.
    if existing_components is not None:
        if (
            existing_components["k"] != k
            or existing_components["mock_mode"] != mock_mode
        ):
            st.session_state.rag_components = None

    if st.session_state.rag_components is None:
        if not os.path.exists(VECTORSTORE_PATH):
            st.error("Vectorstore not found. Run `python ingest.py` first.")
            st.stop()

        try:
            load_rag_system(k, mock_mode)
        except Exception as error:
            st.error(f"Unable to load the assistant: {error}")
            st.stop()

    # Main central layout using tabs for the Chat Window and full Saved Answers list
    tab_chat, tab_saved = st.tabs(["💬 Chat Window", "📚 All Saved Answers"])

    with tab_chat:
        display_chat_history()

        uploaded_file = st.file_uploader(
            "Upload an image, video, or document prompt",
            type=["png", "jpg", "jpeg", "mp4", "mov", "txt", "php"]
        )
        question = st.text_input("Ask a question or describe what you need")

        if st.button("Go"):
            media_bytes = None
            mime_type = None

            if uploaded_file is not None:
                media_bytes = uploaded_file.getvalue()
                mime_type = uploaded_file.type

            with st.chat_message("user"):
                st.markdown(question if question else "Uploaded media prompt")
                if uploaded_file is not None:
                    if mime_type.startswith("image"):
                        st.image(uploaded_file, width=300)
                    elif mime_type.startswith("video"):
                        st.video(uploaded_file)
                    else:
                        st.text(f"Attached file: {uploaded_file.name}")

            with st.chat_message("assistant"):
                try:
                    answer, _, _, from_cache, generated_file_path = query_rag(
                        st.session_state.rag_components,
                        question,
                        use_cache=use_cache,
                        media_bytes=media_bytes,
                        mime_type=mime_type,
                    )

                    # show assistant answer
                    st.markdown(answer)

                    # If the model generated PHP code, provide a download link
                    if generated_file_path and os.path.exists(generated_file_path):
                        with open(generated_file_path, "rb") as f:
                            st.download_button(
                                label="📥 Download Generated PHP File",
                                data=f,
                                file_name=os.path.basename(generated_file_path),
                                mime="text/plain"
                            )

                    if from_cache:
                        st.caption("Saved answer used — Gemini was not called.")

                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer}
                    )

                except Exception as error:
                    st.error(f"Error generating an answer: {error}")

    with tab_saved:
        st.subheader("All Saved Answers")

        cache = load_answer_cache()

        if not cache:
            st.info("No saved answers found.")
        else:
            st.success(f"{len(cache)} saved answers")

            for i, item in enumerate(cache.values(), start=1):
                with st.expander(f"Question {i}: {item['question'][:50]}..."):
                    st.markdown("### Question")
                    st.write(item["question"])
                    st.markdown("### Answer")
                    st.write(item["answer"])

    st.divider()
    st.caption("PHP RAG Assistant | Powered by Gemini, FAISS, and HuggingFace")


if __name__ == "__main__":
    main()