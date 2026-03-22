import sys
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import streamlit as st
from openai import OpenAI
import chromadb
from pathlib import Path
import pandas as pd

DB_PATH = Path("./ChromaDB_for_News")
chroma_client = chromadb.PersistentClient(path=str(DB_PATH))
collection = chroma_client.get_or_create_collection('NewsCollection')

if 'openai_client' not in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=st.secrets.OPEN_API_KEY)
if 'messages' not in st.session_state:
    st.session_state['messages'] = [
        {'role': 'assistant', 'content': 'Ask a question about the news in news.csv.'}]
if "News_VectorDB" not in st.session_state:
    st.session_state.News_VectorDB = collection

def add_to_collection(collection, text, file_name):
    client = st.session_state.openai_client
    response = client.embeddings.create(
        input=text,
        model='text-embedding-3-small')
    embedding = response.data[0].embedding
    collection.add(
        documents=[text],
        ids=[file_name],
        embeddings=[embedding])

def load_csv_to_collection(csv_path, collection):
    df = pd.read_csv(csv_path)
    loaded = 0
    for i, row in df.iterrows():
        text = (
            f"Company: {row['company_name']}\n"
            f"Date: {row['Date']}\n"
            f"Article: {row['Document']}\n"
        )
        file_id = f"article_{i}"
        try:
            add_to_collection(collection, text, file_id)
            loaded += 1
        except Exception:
            pass
    return loaded

def get_interesting_news(df):
    keywords = [
        "lawsuit", "legal", "cfpb", "regulation", "regulatory",
        "investigation", "fraud", "penalty", "fine", "probe",
        "settlement", "doj", "sec", "risk"
    ]
    scored_articles = []
    for i, row in df.iterrows():
        text = str(row["Document"]).lower()
        score = 0
        for word in keywords:
            if word in text:
                score += 1
        scored_articles.append({
            "company_name": row["company_name"],
            "Date": row["Date"],
            "Document": row["Document"],
            "score": score
        })
    ranked_df = pd.DataFrame(scored_articles)
    ranked_df = ranked_df.sort_values(by="score", ascending=False)
    return ranked_df.head(5)

if "csv_loaded" not in st.session_state:
    if collection.count() == 0:
        load_csv_to_collection("./news.csv", collection)
    st.session_state.csv_loaded = True

df_news = pd.read_csv("./news.csv")
st.title('HW7: News Chatbot using RAG')

for msg in st.session_state.messages:
    chat_msg = st.chat_message(msg["role"])
    chat_msg.write(msg["content"])

if prompt := st.chat_input("Ask about the news:"):
    if prompt.lower().strip() == "no":
        st.session_state.messages = [
            {"role": "assistant", "content": "Is there another news story I can help with?"}
        ]
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    rag_context = ""
    rag_used = False

    if prompt.lower().strip() == "find the most interesting news":
        interesting_df = get_interesting_news(df_news)

        blocks = []
        for i, row in interesting_df.iterrows():
            blocks.append(
                f"Company: {row['company_name']}\n"
                f"Date: {row['Date']}\n"
                f"Article: {row['Document']}\n"
                f"Score: {row['score']}"
            )

        rag_context = "\n\n".join(blocks)
        rag_used = True

    else:
        try:
            emb = st.session_state.openai_client.embeddings.create(
                input=prompt,
                model="text-embedding-3-small").data[0].embedding

            results = collection.query(
                query_embeddings=[emb],
                n_results=3)

            docs = results.get("documents", [[]])[0]
            ids_ = results.get("ids", [[]])[0]

            if docs and len(docs) > 0:
                rag_used = True
                blocks = []
                for doc_text, doc_id in zip(docs, ids_):
                    blocks.append(f"SOURCE: {doc_id}\n{doc_text}")
                rag_context = "\n".join(blocks)

        except Exception:
            rag_used = False

    if rag_used == True:
        rag_msg = {
            "role": "system",
            "content": f"RAG CONTEXT:\n{rag_context}"
        }

    system_msg = [{
        'role': 'system',
        'content': (
            'Use the RAG context to answer the prompt only. '
            'If it is not there, respond with I cannot answer that. '
            'If the user asks for the most interesting news, return a ranked list and explain why the stories are interesting.')}]

    client = st.session_state.openai_client

    if rag_used == True:
        stream = client.chat.completions.create(
            model='gpt-4.1',
            messages=system_msg + [rag_msg] + st.session_state.messages,
            stream=True
        )
    else:
        stream = client.chat.completions.create(
            model='gpt-4.1',
            messages=system_msg + st.session_state.messages,
            stream=True
        )

    with st.chat_message("assistant"):
        response = st.write_stream(stream)

    if rag_used == True:
        with st.chat_message("assistant"):
            st.markdown("RAG was used")
    else:
        with st.chat_message("assistant"):
            st.markdown("No RAG content")

    followup = "Would you like more info? (yes/no)"
    with st.chat_message("assistant"):
        st.markdown(followup)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.messages.append({"role": "assistant", "content": followup})
    st.session_state.messages = st.session_state.messages[-4:]