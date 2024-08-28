import os
from dotenv import load_dotenv
import asyncio
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.vectorstores.qdrant import Qdrant
import qdrant_client
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
import tiktoken
import base64
from openai import OpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
# load the variables
load_dotenv()

collection_name = os.getenv("QDRANT_COLLECTION_NAME")


# get the vector stor
def get_vector_store():
    client = qdrant_client.QdrantClient(
        url=os.getenv("QDRANT_HOST"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    embeddings = OpenAIEmbeddings()
    vector_store = Qdrant(
        client=client,
        collection_name=collection_name,
        embeddings=embeddings,
    )
    return vector_store


vector_store = get_vector_store()


def get_context_retriever_chain(vector_store=vector_store):
    llm = ChatOpenAI()
    retriever = vector_store.as_retriever()
    prompt = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            (
                "user",
                "Given the above conversation, generate a search query to look up in order to get information relevant to the conversation",
            ),
        ]
    )
    retriever_chain = create_history_aware_retriever(llm, retriever, prompt)
    return retriever_chain


# Get the conversational RAG chain
def get_conversational_rag_chain(retriever_chain):
    llm = ChatOpenAI()
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                    You are a Pharmaceutical Formulation Specialist trained to address inquiries about pharmaceutical drug formulation and related topics within the pharmaceutical industry.
                    Your responses should strictly adhere to the pharmaceutical field context: {context} you have been trained in. Avoid providing general knowledge answers or responses outside of pharmaceutical formulation.

                    The chatbot is equipped to provide information on various aspects of pharmaceutical drug formulation, including but not limited to:

                    - Drug ingredients and their properties
                    - Dosage forms and their characteristics
                    - Compatibility of ingredients in formulations
                    - Interactions between drugs and excipients
                    - Techniques and methods for drug formulation
                    - Regulatory guidelines and compliance requirements
                    - Drug stability and shelf-life considerations
                    - Solubility enhancement strategies
                    - Dosage form optimization techniques
                    - Industry best practices and standards
                    If a question falls outside of pharmaceutical formulation or exceeds your expertise, reply with: Sorry, I don't know about this as it's beyond my training context as a pharmaceutical formulation AI assistant.
                    Refrain from answering queries on unrelated topics such as religions, sports, programming, and others listed here: [religions, general knowledge, sports, non-pharmaceutical sciences, universe, math, programming, coding, outfits, cultures, ethnicities, management, business, politics, how to make something like food, agriculture, all general knowledge topics except pharmaceuticals, etc.], as they lie outside your scope of expertise. Be polite and recognize greetings like hi, hello, etc.

                """,
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ]
    )
    stuff_documents_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever_chain, stuff_documents_chain)

def get_response(user_input):
    retriever_chain = get_context_retriever_chain(st.session_state.vector_store)
    conversation_rag_chain = get_conversational_rag_chain(retriever_chain)
    response_stream= conversation_rag_chain.stream(
        {"chat_history": st.session_state.chat_history, "input": user_input}
    ) 
    for chunk in response_stream:
        content=chunk.get("answer","")
        yield content
    #return response["answer"]
    # If a response was retrieved, proceed with using it

# convert text back to audio
def text_to_audio(client, text, audio_path):
    response = client.audio.speech.create(model="tts-1", voice="fable", input=text)
    response.stream_to_file(audio_path)

client = OpenAI()

# autoplay audio function
def autoplay_audio(audio_file):
    with open(audio_file, "rb") as audio_file:
        audio_bytes = audio_file.read()
    base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    audio_html = (
        f'<audio src="data:audio/mp3;base64 ,{base64_audio}" controls autoplay>'
    )
    st.markdown(audio_html, unsafe_allow_html=True)

# App layout
st.set_page_config("Dr.Formula Chatbot", "🤖")
with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
title="Dr.Formula"
name = " Developed by:Mohammed Bahageel"
profession = "Artificial Intelligence developer"
imgUrl="https://image.similarpng.com/very-thumbnail/2020/07/Pharmacy-logo-vector-PNG.png"
st.markdown(
    f"""
    <div class="st-emotion-cache-18ni7ap ezrtsby2">
        <a href="{imgUrl}">
            <img class="profileImage" src="{imgUrl}" alt="Your Photo">
        </a>
        <div class="textContainer">
            <div class="title"><p>{title}</p></div>
            <p>{name}</p>
            <p>{profession}</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(
            content=" Hello ! with you is Dr Formula Assistant chatbot  how can I assist you today  with your drug formulation questions related questions? 🥰"
        )
    ]

if "vector_store" not in st.session_state:
    st.session_state.vector_store = get_vector_store()

for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI", avatar="🤖"):
            st.write(message.content)
            response_audio_file = "audio_response.mp3"
            text_to_audio(client, message.content, response_audio_file)
            st.audio(response_audio_file)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human", avatar="👨‍⚕️"):
            st.write(message.content)

# user input
user_query = st.chat_input("Type your message here...")

#response = get_response(user_query)
if user_query is not None and user_query != "":
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    with st.chat_message("Human", avatar="👨‍⚕️"):
        st.markdown(user_query)
    with st.chat_message("AI", avatar="🤖"):
        response=st.write_stream(get_response(user_query))
        response_audio_file = "audio_response.mp3"
        text_to_audio(client, response, response_audio_file)
        autoplay_audio(response_audio_file)
        st.session_state.chat_history.append(AIMessage(content=response))