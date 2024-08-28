

chain = (
    RunnableParallel({
        "context": itemgetter("question"), # | retriever,
        "question": itemgetter("question"),
        "history": itemgetter("history"),
    })
    .assign(response = prompt_template | model | StrOutputParser())
)


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


st.title("Hi, This is AI Me :sunglasses:") 

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

    config2 = {"configurable": {"session_id": "any"}}
    
    with st.chat_message("user"):
        st.write(prompt)

    # Chain - Invoke
    with st.chat_message("assistant"):
        response = chain_with_history.invoke({"question": prompt}, config2)
        #.invoke(
        #    {"question" : prompt, "history" : history},
        #    config={"configurable": {"session_id": "abc123"}},
        #)
        st.write(response['response'])
        
        st.session_state.messages.append({"role": "assistant", "content": response['response']})

#if __name__ == '__main__':
#    main()