import streamlit as st

from components.api_client import api_client


def initialize_chat():

    import uuid

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "pending_action" not in st.session_state:
        st.session_state.pending_action = None


def display_sources(sources):

    if not sources:
        return

    with st.expander("📚 View HR Policy Sources"):

        for source in sources:

            st.markdown(
                f"""
                **Document:** {source.get('document', 'Unknown')}

                **Page:** {source.get('page', 'N/A')}

                **Content:** {source.get('content', '')}
                """
            )

            st.divider()


def display_agent_info(response):

    agent = response.get("agent", "HR Assistant")

    source_type = response.get(
        "source_type",
        "general"
    )

    with st.expander("⚙️ Processing Information"):

        st.write(f"**Agent:** {agent}")

        st.write(f"**Source:** {source_type}")

        if response.get("tool_used"):

            st.write(
                f"**Tool Used:** {response['tool_used']}"
            )


def process_message(message):

    employee_id = st.session_state.employee_id

    try:

        response = api_client.send_chat_message(
            message=message,
            session_id=st.session_state.session_id,
            employee_id=employee_id
        )

        return response

    except Exception as error:

        st.error(
            f"Unable to connect to HR Assistant: {error}"
        )

        return None


def display_chat_history():

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

            if message["role"] == "assistant":

                if message.get("sources"):

                    display_sources(
                        message["sources"]
                    )

                if message.get("metadata"):

                    display_agent_info(
                        message["metadata"]
                    )


def display_suggestions():

    st.markdown("### 💡 Suggested Questions")

    suggestions = [

        "How many annual leaves can I take?",

        "What is my remaining leave balance?",

        "Who is my reporting manager?",

        "Explain casual leave policy.",

        "Show my leave history.",

        "What are the upcoming holidays?"

    ]

    columns = st.columns(2)

    for index, suggestion in enumerate(suggestions):

        with columns[index % 2]:

            if st.button(
                suggestion,
                key=f"suggestion_{index}",
                use_container_width=True
            ):

                st.session_state.user_input = suggestion

                st.rerun()


def handle_chat_input():

    prompt = st.chat_input(
        "Ask anything about HR policies, leaves or employees..."
    )

    if not prompt:

        prompt = st.session_state.pop(
            "user_input",
            None
        )

    if not prompt:
        return

    # Display user message

    st.session_state.messages.append({

        "role": "user",

        "content": prompt

    })

    with st.chat_message("user"):

        st.markdown(prompt)

    # Get assistant response

    with st.chat_message("assistant"):

        with st.spinner("HR Assistant is thinking..."):

            response = process_message(prompt)

            if response is None:
                return

            answer = response.get(
                "answer",
                response.get(
                    "response",
                    "I couldn't generate a response."
                )
            )

            st.markdown(answer)

            sources = response.get("sources", [])

            if sources:

                display_sources(sources)

            display_agent_info(response)

            # Check whether action confirmation is required

            if response.get("requires_confirmation"):

                st.session_state.pending_action = {
                    "action": response.get("action"),
                    "payload": response.get("action_payload"),
                    "confirmation_message": answer
                }

            st.session_state.messages.append({

                "role": "assistant",

                "content": answer,

                "sources": sources,

                "metadata": {

                    "agent": response.get(
                        "agent",
                        "HR Assistant"
                    ),

                    "source_type": response.get(
                        "source_type",
                        "general"
                    ),

                    "tool_used": response.get(
                        "tool_used"
                    )

                }

            })


def render_confirmation():

    pending = st.session_state.pending_action

    if not pending:
        return

    st.warning(
        "⚠️ This operation requires your confirmation."
    )

    st.write(
        pending["confirmation_message"]
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "✅ Confirm",
            use_container_width=True
        ):

            try:

                result = api_client.confirm_action(
                    pending["action"],
                    pending["payload"]
                )

                st.success(
                    result.get(
                        "message",
                        "Operation completed successfully."
                    )
                )

                st.session_state.pending_action = None

                st.rerun()

            except Exception as error:

                st.error(str(error))

    with col2:

        if st.button(
            "❌ Cancel",
            use_container_width=True
        ):

            st.session_state.pending_action = None

            st.info("Operation cancelled.")

            st.rerun()


def render_chat_ui():

    initialize_chat()

    st.title("🤖 AI HR Assistant")

    st.caption(
        "Your intelligent assistant for HR policies, "
        "employee information and leave management."
    )

    st.divider()

    if not st.session_state.messages:

        st.markdown(
            """
            <div style="text-align:center; padding:25px;">

                <h2>👋 Hello! How can I help you?</h2>

                <p>
                Ask me anything about company policies,
                employee information or leave management.
                </p>

            </div>
            """,
            unsafe_allow_html=True
        )

        display_suggestions()

    else:

        display_chat_history()

    render_confirmation()

    handle_chat_input()