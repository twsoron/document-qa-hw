import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic

st.set_page_config(page_title="Lab 2")

st.title("MY Document question answering")
st.write(
    "Upload a document below and ask a question about it – GPT or Claude will answer! "
)

openai_api_key = st.secrets.OPEN_API_KEY
claude_api_key = st.secrets.CLAUDE_API_KEY
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    try:
        client = OpenAI(api_key=openai_api_key)
        client.models.list()
    except:
        st.error("API key not valid ")
        st.stop()

    def read_url_content(url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup.get_text()
        except requests.RequestException as e:
            print(f"Error reading {url}: {e}")
            return None
        
    uploaded_url = st.text_input("Input a URL:")

    question = st.radio(
    "Choose a Summary Option:",
    ["Summarize the document in 100 words", 
     "Summarize the document in 2 connecting paragraphs", 
     "Summarize the document in 5 bullet points"]
    )
    language = st.radio("Choose a Language:", 
    ["English", "French", "Spanish"])
    with st.sidebar:
        llm = st.radio('Choose a LLM:', ["OpenAI", "Claude"])
    
    advanced = st.checkbox("Use advanced Model")
    if llm == 'OpenAI':
        if advanced:
            model = "gpt-4.1"
        else:
            model = "gpt-4.1-nano"
    else:
        if advanced:
            model = "claude-sonnet-4-5"
        else:
            model = "claude-haiku-4-5"
        
    button = st.button("Generate Response")
    if uploaded_url and question and button:
        document = read_url_content(uploaded_url)

        messages = [
            {
                "role": "user",
                "content": f"Here's a document: {document} \n\n---\n\n {question} in {language}",
            }
        ]
        
        if llm == 'OpenAI':
            stream = client.chat.completions.create(
                model= model,
                messages=messages,
                stream=True,)
            st.write_stream(stream)
            
        else:
            client = Anthropic(api_key=claude_api_key)
            with client.messages.stream(
                max_tokens=1024,
                messages=messages,
                model="claude-sonnet-4-5",
            ) as stream:
                full_text = ""
                placeholder = st.empty()
                for chunk in stream.text_stream:
                    full_text += chunk
                    placeholder.text(full_text) 
            
        