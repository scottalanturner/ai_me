# ------------------------------------------------------
# Streamlit
# Knowledge Bases for Amazon Bedrock and LangChain 🦜️🔗
# ------------------------------------------------------

import boto3
from botocore.exceptions import ClientError
import logging
import json
import os

from typing import List, Dict
from pydantic import BaseModel
from operator import itemgetter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_aws import ChatBedrock
from langchain_aws import AmazonKnowledgeBasesRetriever
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from config import config
import streamlit as st
from langchain import hub
import text_to_audio as tta
import base64


def get_secret(secret_name : str, key_name : str) -> str:

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=config.get("region_name")
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret_string = get_secret_value_response['SecretString']
    secret_dict = json.loads(secret_string)

    if key_name in secret_dict:
        return secret_dict[key_name]
    else:
        raise KeyError(f"Key '{key_name}' not found in the secret.")

def get_user_params(user_id: str) -> Dict:
    user_params = None
    # Logic to retrieve user parameters based on user_id
    # This could involve querying a database or using some other method
    # For the sake of this example, we'll use a hardcoded dictionary
    if user_id == "aaron":
        user_params = {
            "prompt_id": "prompt-aaron",
            "voice_id": "giDRC0GdQ7IFfhzcHx2a",
            "knowledge_base_id": "LGSNRAS7OL",
            "bot_name": "AIron",
            "bot_description": "I'm an AI business coach."
        }
    else:
        user_params = {
            "prompt_id": "scott-prompt",
            "voice_id": "wzlHb5hWRmpfSi9CTjhM",
            "knowledge_base_id": "ECROK4NA2O",
            "bot_name": "AI Scott",
            "bot_description": "I'm a personal finance AI that answers questions based on the vast brilliance of Scott Alan Turner, CFP."
        }

    return user_params

# ------------------------------------------------------
# Log level

logging.getLogger().setLevel(logging.ERROR) # reduce log level

# ------------------------------------------------------
# Amazon Bedrock - settings

bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=config.get("region_name"),
)

model_id = config.get("model_id")

model_kwargs =  { 
    "max_tokens": 2048,
    "temperature": 0.0,
    "top_k": 250,
    "top_p": 1,
    "stop_sequences": ["\n\nUser"],
}

## We have the following user specific settings:
# 1. prompt_id
# 2. voice_id
# 3. knowledge_base_id
# 4. name of the person
query_param_user = st.query_params.get("user")
user_params = get_user_params(query_param_user)
prompt_id = user_params['prompt_id']
voice_id = user_params['voice_id']
knowledge_base_id = user_params['knowledge_base_id']
bot_name = user_params['bot_name']
bot_description = user_params['bot_description']
# ------------------------------------------------------
# LangChain - get prompt template

langchain_api_key = get_secret('prod/aime/langchain', 'api_key')
prompt_template = hub.pull(prompt_id, api_key=langchain_api_key)

# ------------------------------------------------------
# ElevenLabs - text-to-speech conversion settings

elevenlabs_api_key = get_secret('prod/aime/elevenlabs', 'api_key')
tta = tta.TextToAudio(elevenlabs_api_key)


# Amazon Bedrock - KnowledgeBase Retriever 
retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id=knowledge_base_id,
    region_name=config.get("region_name"),
    retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 4}},
)

model = ChatBedrock(
    client=bedrock_runtime,
    model_id=model_id,
    model_kwargs=model_kwargs,
)

chain = (
    RunnableParallel({
        "context": itemgetter("question") | retriever,
        "question": itemgetter("question"),
        "chat_history": itemgetter("chat_history"),
    })
    .assign(response = prompt_template | model | StrOutputParser())
    .pick(["response", "context"])
)

# Streamlit Chat Message History
history = StreamlitChatMessageHistory(key="chat_messages")

# Chain with History
chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: history,
    input_messages_key="question",
    history_messages_key="chat_history",
    output_messages_key="response",
)


# Page title
st.title(f"Hi, This is {bot_name} :sunglasses:") 

# Clear Chat History function
def clear_chat_history():
    history.clear()
    st.session_state.messages = [{"role": "assistant", "content": f"I'm {bot_name}! {bot_description}. What can I help you with today?"}]

# Initialize session state for messages if not already present
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"I'm {bot_name}! {bot_description}. What can I help you with today?"}]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat Input - User Prompt 
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)  

    # Chain - Invoke
    with st.chat_message("assistant"):
        response = chain_with_history.invoke(
            {"question" : prompt, "chat_history" : history},
            config = {"configurable": {"session_id": "any"}}
        )
        chat_response = response['response']
        st.write(chat_response)

        # session_state append
        st.session_state.messages.append({"role": "assistant", "content": chat_response})

        audio_stream = tta.text_to_speech_stream(chat_response, voice_id)
        st.audio(audio_stream, format="audio/mpeg", autoplay=True, start_time=0)

# All that work trying to get autoplay to run on IOS was for naught. All of the solutions don't work. Including:
# - inserting the <audio> tag into st.markdown
# - capturing audio bytes and writing them using base64
# - Using an mp3 instead of a stream. This just creates mp3 files stored on the computer (waste of space)
# - Trying to trigger some type of user action. ? The user already interacted with the app.