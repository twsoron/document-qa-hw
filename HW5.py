import sys
__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
import streamlit as st
from openai import OpenAI
import chromadb
from pathlib import Path
from PyPDF2 import PdfReader

DB_PATH = Path("./ChromaDB_for_HW")
chroma_client = chromadb.PersistentClient(path=str(DB_PATH))
collection = chroma_client.get_or_create_collection("HW4_Collection")

if "openai_client" not in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=st.secrets.OPEN_API_KEY)

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant",
        "content": "Ask a question about an IST course at Syracuse University",
        }]

if "Lab4_VectorDB" not in st.session_state:
    st.session_state.Lab4_VectorDB = collection

def add_to_collection(collection, text, file_name):
    client = st.session_state.openai_client
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    embedding = response.data[0].embedding

    collection.add(
        documents=[text],
        ids=[file_name],
        embeddings=[embedding]
    )

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def load_pdfs_to_collection(folder_path: str, collection):
    folder = Path(folder_path)
    pdf_paths = sorted(folder.glob("*.pdf"))
    loaded = 0

    for pdf_path in pdf_paths:
        text = extract_text_from_pdf(str(pdf_path))
        file_id = pdf_path.name

        try:
            add_to_collection(collection, text, file_id)
            loaded += 1
        except Exception:
            pass
    return loaded

def relevant_course_info(query: str, collection, n_results: int = 3):
    client = st.session_state.openai_client
    emb = client.embeddings.create(
        input=query,
        model="text-embedding-3-small").data[0].embedding
    results = collection.query(
        query_embeddings=[emb],
        n_results=n_results
        )

    docs = results.get("documents", [[]])[0]
    if not docs:
        return ""
    return "\n".join(docs)

if collection.count == 0:
    if "HW4_VectorDB" not in st.session_state:
        load_pdfs_to_collection("./HW4_PDF_Data/", collection)
        st.session_state.HW4_VectorDB = collection


st.title("HW5: Chatbot using RAG function")

for msg in st.session_state.messages:
    chat_msg = st.chat_message(msg["role"])
    chat_msg.write(msg["content"])

if prompt := st.chat_input("Ask about a course:"):
    if prompt.lower().strip() == "no":
        st.session_state.messages = [
            {"role": "assistant", "content": "Is there another course I can help with?"}
        ]
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    rag_used = False
    rag_context = ""
    rag_msg = {"role": "system", "content": ""}

    try:
        rag_context = relevant_course_info(prompt, collection, n_results=3)
        if rag_context.strip():
            rag_used = True
            rag_msg = {"role": "system", "content": f"RAG CONTEXT:\n{rag_context}"}
    except Exception:
        rag_used = False

    system_msg = [
        {
            "role": "system",
            "content": "Use the RAG context to answer the prompt only, if it is not there respond with I cannot answer that",
        }
    ]

    client = st.session_state.openai_client
    stream = client.chat.completions.create(
        model="gpt-4.1",
        messages=system_msg + [rag_msg] + st.session_state.messages,
        stream=True
    )

    with st.chat_message("assistant"):
        response = st.write_stream(stream)

    if rag_used == True:
        rag_usage = "RAG was used"
        with st.chat_message("assistant"):
            st.markdown(rag_usage)
    else:
        no_rag_usage = "No RAG content"
        with st.chat_message("assistant"):
            st.markdown(no_rag_usage)

    followup = "Would you like more info? (yes/no)"
    with st.chat_message("assistant"):
        st.markdown(followup)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.messages.append({"role": "assistant", "content": followup})
    st.session_state.messages = st.session_state.messages[-6:]