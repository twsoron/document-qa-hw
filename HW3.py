
import streamlit as st
from openai import OpenAI
from anthropic import Anthropic
import requests
from bs4 import BeautifulSoup

system_msg = [{'role': 'system', 'content': 'Explain the response so a 10 year old can understand, keep answers to a medium length.'}]
if 'client' not in st.session_state:
    openai_api_key = st.secrets.OPEN_API_KEY
    st.session_state.client = OpenAI(api_key=openai_api_key)
if 'claudeclient' not in st.session_state:
    claude_api_key = st.secrets.CLAUDE_API_KEY
    st.session_state.claudeclient = Anthropic(api_key=claude_api_key)

if 'messages' not in st.session_state:
    st.session_state['messages'] = [{'role': 'assistant', 'content': 'How can I help you?'}]

def read_url_content(url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup.get_text()
        except requests.RequestException as e:
            print(f"Error reading {url}: {e}")
            return None
        
with st.sidebar:
    llm = st.radio('Choose a LLM:', ['OpenAI','Claude'])

with st.sidebar: 
    url1 = st.text_input('Enter URL(s):')
    url2 = st.text_input('')

for msg in st.session_state.messages:
    chat_msg = st.chat_message(msg["role"])
    chat_msg.write(msg["content"])

if llm == 'OpenAI':
    model = 'gpt-5.2'
else:
    model = 'claude-opus-4-6'

if prompt := st.chat_input("What is up?"):

    if prompt.lower().strip() == "no":
        st.session_state.messages = [
            {"role": "assistant", "content": "Anything else I can help with?"}]
        st.rerun()
    url_text = ""
    if url1 or url2: 
        if url1:
            url1_text = read_url_content(url1)
            url_text += f'url 1 content: {url1_text}'
        if url2:
            url2_text = read_url_content(url2)
            url_text += f'url 2 content: {url2_text}'
        url_prompt = [{"role": "user", "content": f"URL TEXT: \n{url_text}"}]
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    

    with st.chat_message("user"):
        st.markdown(prompt)
    if llm == 'OpenAI':
        client = st.session_state.client
        stream = client.chat.completions.create(
            model= 'gpt-4.1',
            messages= system_msg + st.session_state.messages + url_prompt,
            stream=True
        )
      
    else:
        claudeclient = st.session_state.claudeclient
        with st.chat_message("assistant"):
            full_text = ""
            placeholder = st.empty()

            with claudeclient.messages.stream(
                max_tokens=1024,
                system=[{"type": "text", "text":'Explain the response so a 10 year old can understand, keep answers to a medium length.' }],
                messages=st.session_state.messages + url_prompt,
                model="claude-opus-4-6",
            ) as stream:
                for chunk in stream.text_stream:
                    full_text += chunk
                    placeholder.markdown(full_text)

            response = full_text      
    if llm == 'OpenAI':
        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        
        followup = "Would you like more info? (yes/no)"
        with st.chat_message("assistant"):
            st.markdown(followup)
    else:
        followup = "Would you like more info? (yes/no)"
        with st.chat_message("assistant"):
            st.markdown(followup)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.messages.append({"role": "assistant", "content": followup})
    st.session_state.messages = st.session_state.messages[-6:]
