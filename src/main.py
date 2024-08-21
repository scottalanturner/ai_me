import streamlit as st 
import src.chatbot_backend as cb
import src.text_to_speech_stream as tts

# Set Title for Chatbot - https://docs.streamlit.io/library/api-reference/text/st.title
st.title("Hi, This is AI Me :sunglasses:") 

# LangChain memory to the session cache - Session State - https://docs.streamlit.io/library/api-reference/session-state
if 'memory' not in st.session_state: 
    st.session_state.memory = cb.chat_memory() #** Modify the import and memory function() attributes initialize the memory

# Add the UI chat history to the session cache - Session State - https://docs.streamlit.io/library/api-reference/session-state
if 'history' not in st.session_state: #see if the chat history hasn't been created yet
    st.session_state.chat_history = [] #initialize the chat history

# Re-render the chat history (Streamlit re-runs this script, so need this to preserve previous chat messages)
for message in st.session_state.chat_history: 
    with st.chat_message(message["role"]): 
        st.markdown(message["text"]) 

# Enter the details for chatbot input box
input_text = st.chat_input("How can I help you today?") # **display a chat input box
if input_text: 
    
    with st.chat_message("user"): 
        st.markdown(input_text) 
    
    st.session_state.chat_history.append({"role":"user", "text":input_text}) 

    chat_response = cb.conversation(input_text=input_text, memory=st.session_state.memory) 
    
    with st.chat_message("assistant"): 
        st.markdown(chat_response) 
    
    st.session_state.chat_history.append({"role":"assistant", "text":chat_response}) 

    # Convert to voice
    audio_stream = tts.text_to_speech_stream(chat_response) 

    # Display the audio in a player
    st.audio(audio_stream, format="audio/mp3", autoplay=True, start_time=0)