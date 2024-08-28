import streamlit as st
import boto3
from config import config
from langchain_core.prompts import ChatPromptTemplate
from langchain_aws import ChatBedrock, AmazonKnowledgeBasesRetriever
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableParallel
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from botocore.exceptions import ClientError
import os
import json
from operator import itemgetter

def get_prompt_template() -> ChatPromptTemplate:
    template = '''Answer the question using the following context along with your existing knowledge. If you don't know the answer, please say so.

Your response should:
- Reflect the tone of voice (casual, friendly) of the content writer.
- Incorporate specific phrases, idioms, or jargon that are characteristic of the content writer, ensuring no use of profanity or swearing.
- Match the pacing and rhythm of the content writer, using concise, impactful sentences.
- Use sentence structures and complexity that mirror the content writer's style.
- Convey the same emotional undertone (enthusiasm, skepticism, calmness, etc.) found in the context.
- Maintain the same point of view as the content writer, whether it's first person, third person, etc.
- Include cultural or contextual references that align with those found in the context, without resorting to inappropriate language.
- Use light humor if it matches the style of the content writer, ensuring it remains respectful and free of offensive language.

    Context:
    {context}

    History:
    {history}

    Question: {question}'''

    prompt = ChatPromptTemplate.from_template(template)

    return prompt

def get_model():
    session = boto3.session.Session()

    # bedrock client, using the session credential for the region
    client = session.client(
        service_name='bedrock-runtime',
        region_name=config.get('region_name')
    )

    # Change this to experiment with different models
    model_id = config.get('model_id')

    model_kwargs =  { 
        "max_tokens": 2048,
        "temperature": 0.0,
        "top_k": 250,
        "top_p": 1,
        "stop_sequences": ["\n\nHuman"],
    }

    model = ChatBedrock(
        client=client,
        model_id=model_id,
        model_kwargs=model_kwargs,
    )
    return model

def get_knowledge_base_retriever():
    # Amazon Bedrock - KnowledgeBase Retriever 
    retriever = AmazonKnowledgeBasesRetriever(
        knowledge_base_id=config.get('knowledge_base_id'),
        region=config.get('region_name'),
        retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 4}},
        #client=client, # If you use this, the error Bedrock has no attribute 'retrieve' will happen
    )
    return retriever



model = get_model()

prompt_template = get_prompt_template()

retriever = get_knowledge_base_retriever()

chain = prompt_template | model | StrOutputParser()

# Streamlit Chat Message History
history = StreamlitChatMessageHistory(key="chat_messages")

# Chain with History
chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: history,  # Always return the instance created earlier
    input_messages_key="question",
    history_messages_key="history",
)


if history.messages == []:
    history.add_ai_message("How may I assist you today?")

for msg in history.messages:
    st.chat_message(msg.type).write(msg.content)

# Chat Input - User Prompt 
if prompt := st.chat_input():
    st.chat_message("human").write(prompt)

    #with st.chat_message("user"):
    #    st.write(prompt)
        
    # As usual, new messages are added to StreamlitChatMessageHistory when the Chain is called.
    config2 = {"configurable": {"session_id": "any"}}

    with st.chat_message("assistant"):
        # Chain - Invoke
        response = chain_with_history.invoke({"question": prompt}, config2)
        st.chat_message("ai").write(response)