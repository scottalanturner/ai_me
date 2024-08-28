import boto3

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_aws import ChatBedrock
from langchain_aws import AmazonKnowledgeBasesRetriever
from config import config
from langchain_core.runnables.history import RunnableWithMessageHistory

region_name = config.get('region_name')

session = boto3.session.Session()

# bedrock client, using the session credential for the region
client = session.client(
    service_name='bedrock-runtime',
    region_name=region_name
)

# Change this to experiment with different models
model_id = config.get('model_id')

model_id = "anthropic.claude-instant-v1"

model_kwargs =  { 
    "max_tokens": 2048,
    "temperature": 0.0,
    "top_k": 250,
    "top_p": 1,
    "stop_sequences": ["\n\nHuman"],
}

# ------------------------------------------------------
# LangChain - RAG chain with citations

template = '''Answer the question using the following context along with your existing knowledge. If you don't know the answer, please say so.

Your response should:
- Reflect the tone of voice (casual, friendly) of the content writer.
- Incorporate specific phrases, idioms, or jargon that are characteristic of the content writer.
- Match the pacing and rhythm of the content writer, using short, punchy sentences.
- Use sentence structures and complexity that mirror the content writer's style.
- Convey the same emotional undertone (enthusiasm, skepticism, calmness, etc.) found in the context.
- Maintain the same point of view as the content writer, whether it's first person, third person, etc.
- Include cultural or contextual references that align with those found in the context.
- Incorporate humor or sarcasm if it matches the style of the content writer.

Context:
{context}

Question: {question}'''

prompt = ChatPromptTemplate.from_template(template)

# Amazon Bedrock - KnowledgeBase Retriever 
retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id="MOG3JEYBHU", # 👈 Set your Knowledge base ID
    retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 4}},
)

model = ChatBedrock(
    client=client,
    model_id=model_id,
    model_kwargs=model_kwargs,
)
from operator import itemgetter

chain = (
    RunnableParallel({
        "context": itemgetter("question") | retriever,
        "question": itemgetter("question"),
        "history": itemgetter("history"),
    })
    .assign(response = prompt | model | StrOutputParser())
)

# ------------------------------------------------------
# Streamlit

import streamlit as st
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

# Streamlit Chat Message History
history = StreamlitChatMessageHistory(key="chat_messages")

# Chain with History
chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: history,
    input_messages_key="question",
    history_messages_key="history",
    output_messages_key="response",
)




# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat Input - User Prompt 
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)

    config = {"configurable": {"session_id": "any"}}

    # Chain - Invoke
    with st.chat_message("assistant"):
        response = chain_with_history.invoke(
            {"question" : prompt, "history" : history},
            config
        )
        st.write(response['response'])
        
        st.session_state.messages.append({"role": "assistant", "content": response['response']})