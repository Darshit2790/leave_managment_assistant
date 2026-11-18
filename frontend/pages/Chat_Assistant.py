import streamlit as st
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components.api_client import send_chat_message

st.set_page_config(
    page_title="AI Leave Assistant",
    page_icon="🤖",
    layout="wide"
)

# -------------------------------
# Session Initialization
# -------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "employee_id" not in st.session_state:
    st.session_state.employee_id = "EMP001"


# -------------------------------
# Page Header
# -------------------------------

st.title("🤖 Leave Management Assistant")

st.caption(
    "Ask me anything about leave policies, "
    "leave balance and leave applications."
)

st.divider()


# -------------------------------
# Suggested Questions
# -------------------------------

if not st.session_state.messages:

    st.subheader("How can I help you today?")

    suggestions = [
        "What is the casual leave policy?",
        "How many leaves do I have?",
        "I want to apply for leave.",
        "How can I cancel my leave?",
        "What are the upcoming holidays?"
    ]

    cols = st.columns(2)

    for index, question in enumerate(suggestions):

        with cols[index % 2]:

            if st.button(
                question,
                use_container_width=True
            ):
                st.session_state.pending_prompt = question
                st.rerun()


# -------------------------------
# Display Chat History
# -------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# -------------------------------
# Process User Input
# -------------------------------

prompt = st.chat_input(
    "Type your message here..."
)

if "pending_prompt" in st.session_state:

    prompt = st.session_state.pending_prompt

    del st.session_state.pending_prompt


if prompt:

    # Display User Message

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)


    # Get AI Response

    with st.chat_message("assistant"):

        with st.spinner("AI Assistant is thinking..."):

            result = send_chat_message(
                message=prompt,
                employee_id=st.session_state.employee_id,
                session_id=st.session_state.session_id
            )

            answer = result.get(
                "response",
                "Sorry, I couldn't process your request."
            )

            st.markdown(answer)

            # Display Agent Information

            agent_name = result.get("agent")

            if agent_name:
                st.caption(f"Handled by: {agent_name}")

            # Display RAG source information

            sources = result.get("sources", [])

            if sources:

                with st.expander("📚 Knowledge Sources"):

                    for source in sources:
                        st.write(f"• {source}")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })


# -------------------------------
# Clear Conversation
# -------------------------------

with st.sidebar:

    st.subheader("Chat Settings")

    st.write(
        f"Employee ID: {st.session_state.employee_id}"
    )

    if st.button("🗑️ Clear Conversation"):

        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())

        st.rerun()