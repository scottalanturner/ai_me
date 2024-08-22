import streamlit as st
from chatbot import ChatBot

def go_frontend():

    chatbot = ChatBot()
    chatbot.init_model()

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
            response = chatbot.chain_with_history.invoke(
                {"question" : prompt, "history" : chatbot.history},
                config
            )
            st.write(response['response'])
            
            st.session_state.messages.append({"role": "assistant", "content": response['response']})

if __name__ == '__main__':
    go_frontend()