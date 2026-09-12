import streamlit as st
import uuid
import os
import tempfile
import sqlite3
import time

# ============================================================
# BACKEND
# ============================================================

from agentic_chatbot_hitl_backend import (
    chatbot,
    get_all_threads,
    ingest_rag_document
)

# ============================================================
# LANGCHAIN MESSAGES
# ============================================================

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    BaseMessage
)

# ============================================================
# LANGGRAPH HITL
# ============================================================

from langgraph.types import Command


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Agent Chatbot",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Agent Chatbot with LangGraph")


# ============================================================
# CHAT METADATA DATABASE
# ============================================================

CHAT_METADATA_DB = "chat_metadata.db"


def init_chat_metadata_db():

    conn = sqlite3.connect(
        CHAT_METADATA_DB
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            thread_id TEXT PRIMARY KEY,
            title TEXT,
            last_active REAL
        )
        """
    )

    conn.commit()

    conn.close()


init_chat_metadata_db()


# ============================================================
# GENERATE THREAD ID
# ============================================================

def generate_thread_id():

    return str(uuid.uuid4())


# ============================================================
# GENERATE CHAT TITLE
# ============================================================

def generate_chat_title(message):

    title = message.strip()

    # Remove extra spaces
    title = " ".join(
        title.split()
    )

    # Remove question mark
    title = title.replace(
        "?",
        ""
    )

    prefixes = [

        "how do i ",
        "how can i ",
        "what is ",
        "what are ",
        "can you ",
        "could you ",
        "please ",
        "help me ",
        "help me understand ",
        "explain ",
        "tell me about ",
        "i want to ",
        "i need to ",
        "i need help with ",
        "show me ",
        "give me "

    ]

    lower_title = title.lower()

    for prefix in prefixes:

        if lower_title.startswith(
            prefix
        ):

            title = title[
                len(prefix):
            ]

            break


    title = title.strip()


    if title:

        title = (
            title[0].upper()
            + title[1:]
        )


    # Maximum title length
    if len(title) > 45:

        title = (
            title[:45].strip()
            + "..."
        )


    if not title:

        title = "New Conversation"


    return title


# ============================================================
# LOAD CONVERSATION
# ============================================================

def load_conversation(thread_id):

    state = chatbot.get_state(

        config={
            "configurable": {
                "thread_id": thread_id
            }
        }

    )

    return state.values.get(
        "messages",
        []
    )


# ============================================================
# CONVERT LANGCHAIN MESSAGES
# ============================================================

def convert_messages(messages):

    converted = []


    for message in messages:

        # ----------------------------------------------------
        # USER
        # ----------------------------------------------------

        if isinstance(
            message,
            HumanMessage
        ):

            if isinstance(
                message.content,
                str
            ):

                converted.append({

                    "role": "user",

                    "content":
                        message.content

                })


        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        elif isinstance(
            message,
            AIMessage
        ):

            if (

                isinstance(
                    message.content,
                    str
                )

                and

                message.content.strip()

            ):

                converted.append({

                    "role": "assistant",

                    "content":
                        message.content

                })


        # ----------------------------------------------------
        # TOOL
        # ----------------------------------------------------

        elif isinstance(
            message,
            ToolMessage
        ):

            continue


    return converted


# ============================================================
# GET THREAD TITLE
# ============================================================

def get_thread_title(thread_id):

    try:

        messages = load_conversation(
            thread_id
        )


        for message in messages:

            if isinstance(
                message,
                HumanMessage
            ):

                return generate_chat_title(
                    message.content
                )


    except Exception:

        pass


    return "Conversation"


# ============================================================
# SAVE CHAT METADATA
# ============================================================

def save_chat_metadata(
    thread_id,
    title,
    last_active=None
):

    if last_active is None:

        last_active = time.time()


    conn = sqlite3.connect(
        CHAT_METADATA_DB
    )

    cursor = conn.cursor()


    cursor.execute(

        """
        INSERT INTO chats
        (
            thread_id,
            title,
            last_active
        )

        VALUES (?, ?, ?)

        ON CONFLICT(thread_id)

        DO UPDATE SET

            title = excluded.title,

            last_active =
                excluded.last_active
        """,

        (
            thread_id,
            title,
            last_active
        )

    )


    conn.commit()

    conn.close()


# ============================================================
# UPDATE CHAT ACTIVITY
# ============================================================

def update_chat_activity(
    thread_id
):

    conn = sqlite3.connect(
        CHAT_METADATA_DB
    )

    cursor = conn.cursor()


    cursor.execute(

        """
        UPDATE chats

        SET last_active = ?

        WHERE thread_id = ?
        """,

        (
            time.time(),
            thread_id
        )

    )


    conn.commit()

    conn.close()


# ============================================================
# UPDATE CHAT TITLE
# ============================================================

def update_chat_title(
    thread_id,
    title
):

    conn = sqlite3.connect(
        CHAT_METADATA_DB
    )

    cursor = conn.cursor()


    cursor.execute(

        """
        UPDATE chats

        SET title = ?

        WHERE thread_id = ?
        """,

        (
            title,
            thread_id
        )

    )


    conn.commit()

    conn.close()


# ============================================================
# GET ALL CHAT METADATA
# ============================================================

def get_chat_metadata():

    conn = sqlite3.connect(
        CHAT_METADATA_DB
    )

    cursor = conn.cursor()


    cursor.execute(

        """
        SELECT
            thread_id,
            title,
            last_active

        FROM chats

        ORDER BY last_active DESC
        """

    )


    rows = cursor.fetchall()

    conn.close()


    chats = []


    for row in rows:

        chats.append({

            "id": row[0],

            "title": row[1],

            "last_active": row[2]

        })


    return chats


# ============================================================
# REGISTER OLD THREADS
# ============================================================

def register_existing_thread(
    thread_id
):

    existing = get_chat_metadata()


    for chat in existing:

        if chat["id"] == thread_id:

            return


    title = get_thread_title(
        thread_id
    )


    if title == "Conversation":

        return


    save_chat_metadata(

        thread_id,

        title,

        time.time()

    )


# ============================================================
# CREATE NEW CHAT
# ============================================================

def create_new_chat():

    thread_id = generate_thread_id()


    # Current thread
    st.session_state[
        "thread_id"
    ] = thread_id


    # Clear messages
    st.session_state[
        "message_history"
    ] = []


    # Clear HITL
    st.session_state[
        "pending_hitl"
    ] = None


    # Temporary title
    st.session_state[
        "current_chat_title"
    ] = "New Conversation"


    # Save new chat
    save_chat_metadata(

        thread_id,

        "New Conversation",

        time.time()

    )


# ============================================================
# OPEN THREAD
# ============================================================

def open_thread(
    thread_id
):

    # --------------------------------------------------------
    # Set current thread
    # --------------------------------------------------------

    st.session_state[
        "thread_id"
    ] = thread_id


    # --------------------------------------------------------
    # Load messages
    # --------------------------------------------------------

    messages = load_conversation(
        thread_id
    )


    # --------------------------------------------------------
    # Convert messages
    # --------------------------------------------------------

    st.session_state[
        "message_history"
    ] = convert_messages(
        messages
    )


    # --------------------------------------------------------
    # Get title
    # --------------------------------------------------------

    title = get_thread_title(
        thread_id
    )


    if title == "Conversation":

        title = "New Conversation"


    st.session_state[
        "current_chat_title"
    ] = title


    # --------------------------------------------------------
    # Make this conversation most recent
    # --------------------------------------------------------

    update_chat_activity(
        thread_id
    )


    # --------------------------------------------------------
    # Check HITL
    # --------------------------------------------------------

    sync_pending_interrupt(
        thread_id
    )


# ============================================================
# ============================================================
# HUMAN-IN-THE-LOOP FUNCTIONS
# ============================================================
# ============================================================


# ============================================================
# GET PENDING INTERRUPT
# ============================================================

def get_pending_interrupt(
    thread_id
):

    """
    Check whether LangGraph is currently
    waiting for human input.
    """

    config = {

        "configurable": {

            "thread_id":
                thread_id

        }

    }


    try:

        state_snapshot = chatbot.get_state(
            config
        )


        # ----------------------------------------------------
        # Some LangGraph versions expose interrupts directly
        # ----------------------------------------------------

        direct_interrupts = getattr(

            state_snapshot,

            "interrupts",

            ()

        ) or ()


        if direct_interrupts:

            return direct_interrupts[0]


        # ----------------------------------------------------
        # Other versions expose interrupts inside tasks
        # ----------------------------------------------------

        tasks = getattr(

            state_snapshot,

            "tasks",

            ()

        ) or ()


        for task in tasks:

            task_interrupts = getattr(

                task,

                "interrupts",

                ()

            ) or ()


            if task_interrupts:

                return task_interrupts[0]


    except Exception:

        return None


    return None


# ============================================================
# SAVE PENDING INTERRUPT
# ============================================================

def save_pending_interrupt(
    thread_id,
    interrupt_object
):

    st.session_state[
        "pending_hitl"
    ] = {

        "thread_id":
            thread_id,

        "prompt":
            str(
                interrupt_object.value
            )

    }


# ============================================================
# SYNCHRONIZE HITL STATE
# ============================================================

def sync_pending_interrupt(
    thread_id
):

    pending_interrupt = (
        get_pending_interrupt(
            thread_id
        )
    )


    if pending_interrupt is not None:

        save_pending_interrupt(

            thread_id,

            pending_interrupt

        )


    else:

        current_pending = (
            st.session_state.get(
                "pending_hitl"
            )
        )


        if (

            current_pending is not None

            and

            current_pending.get(
                "thread_id"
            )
            == thread_id

        ):

            st.session_state[
                "pending_hitl"
            ] = None


# ============================================================
# RESUME INTERRUPTED GRAPH
# ============================================================

def resume_hitl_execution(
    decision
):

    pending_hitl = (
        st.session_state.get(
            "pending_hitl"
        )
    )


    if not pending_hitl:

        st.warning(
            "There is no pending action."
        )

        return


    # --------------------------------------------------------
    # IMPORTANT:
    # Use SAME thread ID
    # --------------------------------------------------------

    interrupted_thread_id = (
        pending_hitl[
            "thread_id"
        ]
    )


    resume_config = {

        "configurable": {

            "thread_id":
                interrupted_thread_id

        },

        "metadata": {

            "thread_id":
                interrupted_thread_id

        },

        "run_name":
            "hitl_resume_trace"

    }


    try:

        with st.chat_message(
            "assistant"
        ):

            status_box = st.status(

                "🔄 Continuing...",

                expanded=True

            )


            def resumed_stream():

                for (

                    message_chunk,

                    metadata

                ) in chatbot.stream(

                    Command(
                        resume=decision
                    ),

                    config=resume_config,

                    stream_mode="messages"

                ):


                    # ----------------------------------------
                    # TOOL
                    # ----------------------------------------

                    if isinstance(

                        message_chunk,

                        ToolMessage

                    ):

                        tool_name = getattr(

                            message_chunk,

                            "name",

                            "tool"

                        )


                        status_box.update(

                            label=
                                f"🔧 Using `{tool_name}`...",

                            state="running",

                            expanded=True

                        )


                    # ----------------------------------------
                    # AI
                    # ----------------------------------------

                    if isinstance(

                        message_chunk,

                        AIMessage

                    ):

                        content = (
                            message_chunk.content
                        )


                        if (

                            isinstance(
                                content,
                                str
                            )

                            and content

                        ):

                            yield content


            resumed_ai_message = (
                st.write_stream(
                    resumed_stream()
                )
            )


            # ----------------------------------------------
            # CHECK ANOTHER INTERRUPT
            # ----------------------------------------------

            next_interrupt = (
                get_pending_interrupt(
                    interrupted_thread_id
                )
            )


            if next_interrupt is not None:

                save_pending_interrupt(

                    interrupted_thread_id,

                    next_interrupt

                )


                status_box.update(

                    label=
                        "⚠️ Another approval is required",

                    state="complete",

                    expanded=False

                )


            else:

                st.session_state[
                    "pending_hitl"
                ] = None


                status_box.update(

                    label=
                        "✅ Action completed",

                    state="complete",

                    expanded=False

                )


        # ----------------------------------------------------
        # Save response
        # ----------------------------------------------------

        if resumed_ai_message:

            st.session_state[
                "message_history"
            ].append({

                "role":
                    "assistant",

                "content":
                    resumed_ai_message

            })


        # ----------------------------------------------------
        # Update recent order
        # ----------------------------------------------------

        update_chat_activity(
            interrupted_thread_id
        )


        st.rerun()


    except Exception as error:

        st.error(

            "Could not resume the action: "
            f"{error}"

        )


# ============================================================
# RAG DOCUMENT INGESTION
# ============================================================

def ingest_uploaded_document(
    uploaded_file
):

    extension = os.path.splitext(
        uploaded_file.name
    )[1].lower()


    allowed_extensions = [

        ".pdf",
        ".txt",
        ".md",
        ".csv"

    ]


    if extension not in allowed_extensions:

        st.error(
            "Please upload PDF, TXT, MD or CSV."
        )

        return False


    temp_file = tempfile.NamedTemporaryFile(

        delete=False,

        suffix=extension

    )


    try:

        temp_file.write(
            uploaded_file.getbuffer()
        )

        temp_file.close()


        result = ingest_rag_document(
            temp_file.name
        )


        return result


    except Exception as error:

        st.error(
            f"Document ingestion failed: {error}"
        )

        return False


    finally:

        try:

            os.unlink(
                temp_file.name
            )

        except Exception:

            pass


# ============================================================
# SESSION STATE
# ============================================================

if "thread_id" not in st.session_state:

    st.session_state[
        "thread_id"
    ] = None


if "message_history" not in st.session_state:

    st.session_state[
        "message_history"
    ] = []


if "current_chat_title" not in st.session_state:

    st.session_state[
        "current_chat_title"
    ] = None


if "uploaded_documents" not in st.session_state:

    st.session_state[
        "uploaded_documents"
    ] = []


# ============================================================
# HITL SESSION STATE
# ============================================================

if "pending_hitl" not in st.session_state:

    st.session_state[
        "pending_hitl"
    ] = None


# ============================================================
# REGISTER EXISTING THREADS
# ============================================================

try:

    existing_threads = get_all_threads()


    for thread in existing_threads:

        if isinstance(
            thread,
            str
        ):

            register_existing_thread(
                thread
            )


        elif isinstance(
            thread,
            dict
        ):

            thread_id = thread.get(
                "id"
            )


            if thread_id:

                register_existing_thread(
                    thread_id
                )


except Exception as error:

    st.sidebar.error(
        f"Could not load old chats: {error}"
    )


# ============================================================
# GET CHAT LIST
# ============================================================

chat_threads = get_chat_metadata()


# ============================================================
# AUTOMATICALLY OPEN MOST RECENT CHAT
# ============================================================

if st.session_state[
    "thread_id"
] is None:

    if chat_threads:

        latest_chat = chat_threads[0]


        open_thread(
            latest_chat["id"]
        )


    else:

        create_new_chat()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "💬 My Conversations"
)


# ============================================================
# NEW CHAT
# ============================================================

if st.sidebar.button(

    "➕ New Chat",

    use_container_width=True

):

    create_new_chat()

    st.rerun()


st.sidebar.divider()


# ============================================================
# KNOWLEDGE BASE
# ============================================================

st.sidebar.subheader(
    "📚 Knowledge Base"
)


uploaded_file = st.sidebar.file_uploader(

    "Upload a document",

    type=[

        "pdf",

        "txt",

        "md",

        "csv"

    ]

)


# ============================================================
# ADD TO KNOWLEDGE BASE
# ============================================================

if uploaded_file is not None:

    if st.sidebar.button(

        "📥 Add to Knowledge Base",

        use_container_width=True

    ):

        with st.spinner(
            "Processing document..."
        ):

            result = (
                ingest_uploaded_document(
                    uploaded_file
                )
            )


        if result:

            if uploaded_file.name not in (

                st.session_state[
                    "uploaded_documents"
                ]

            ):

                st.session_state[
                    "uploaded_documents"
                ].append(
                    uploaded_file.name
                )


            st.sidebar.success(
                "✅ Document added!"
            )


st.sidebar.divider()


# ============================================================
# DOCUMENT LIST
# ============================================================

if st.session_state[
    "uploaded_documents"
]:

    st.sidebar.caption(
        "📄 Documents"
    )


    for document in (

        st.session_state[
            "uploaded_documents"
        ]

    ):

        st.sidebar.caption(
            f"• {document}"
        )


st.sidebar.divider()


# ============================================================
# REFRESH CHAT LIST
# ============================================================

chat_threads = get_chat_metadata()


# ============================================================
# DISPLAY CHATS
#
# MOST RECENT / CURRENT
#          ↓
# PREVIOUS
#          ↓
# OLDER
#          ↓
# OLDEST
# ============================================================

for chat in chat_threads:

    thread_id = chat["id"]

    title = chat["title"]


    if (

        thread_id
        ==
        st.session_state[
            "thread_id"
        ]

    ):

        button_text = (
            f"🟢 {title}"
        )

    else:

        button_text = (
            f"💬 {title}"
        )


    if st.sidebar.button(

        button_text,

        key=f"chat_{thread_id}",

        use_container_width=True

    ):

        open_thread(
            thread_id
        )

        st.rerun()


# ============================================================
# CURRENT CHAT TITLE
# ============================================================

if st.session_state[
    "current_chat_title"
]:

    st.caption(

        "💬 "
        +
        st.session_state[
            "current_chat_title"
        ]

    )


# ============================================================
# DISPLAY CONVERSATION
# ============================================================

for message in (

    st.session_state[
        "message_history"
    ]

):

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# ============================================================
# HUMAN-IN-THE-LOOP UI
# ============================================================

pending_hitl = (
    st.session_state.get(
        "pending_hitl"
    )
)


current_thread_has_pending_hitl = (

    pending_hitl is not None

    and

    pending_hitl.get(
        "thread_id"
    )
    ==
    st.session_state[
        "thread_id"
    ]

)


# ============================================================
# SHOW APPROVAL REQUEST
# ============================================================

if current_thread_has_pending_hitl:

    st.warning(

        "🧑 **Human approval required**\n\n"

        + pending_hitl[
            "prompt"
        ]

    )


    approve_col, reject_col = (
        st.columns(2)
    )


    # --------------------------------------------------------
    # APPROVE
    # --------------------------------------------------------

    with approve_col:

        if st.button(

            "✅ Approve",

            key=
                f"approve_{st.session_state['thread_id']}",

            type="primary",

            use_container_width=True

        ):

            resume_hitl_execution(
                "yes"
            )


    # --------------------------------------------------------
    # REJECT
    # --------------------------------------------------------

    with reject_col:

        if st.button(

            "❌ Reject",

            key=
                f"reject_{st.session_state['thread_id']}",

            use_container_width=True

        ):

            resume_hitl_execution(
                "no"
            )


# ============================================================
# CHAT INPUT
# ============================================================

user_input = st.chat_input(

    "Ask anything...",

    disabled=
        current_thread_has_pending_hitl

)


# ============================================================
# PROCESS USER MESSAGE
# ============================================================

if user_input:

    current_thread_id = (
        st.session_state[
            "thread_id"
        ]
    )


    # ========================================================
    # CHECK FIRST MESSAGE
    # ========================================================

    is_first_message = (

        len(
            st.session_state[
                "message_history"
            ]
        )
        ==
        0

    )


    # ========================================================
    # CREATE CHAT TITLE
    # ========================================================

    if is_first_message:

        title = generate_chat_title(
            user_input
        )


        st.session_state[
            "current_chat_title"
        ] = title


        update_chat_title(

            current_thread_id,

            title

        )


    # ========================================================
    # UPDATE RECENT ACTIVITY
    # ========================================================

    update_chat_activity(
        current_thread_id
    )


    # ========================================================
    # SAVE USER MESSAGE TO UI
    # ========================================================

    st.session_state[
        "message_history"
    ].append({

        "role": "user",

        "content": user_input

    })


    # ========================================================
    # DISPLAY USER MESSAGE
    # ========================================================

    with st.chat_message(
        "user"
    ):

        st.markdown(
            user_input
        )


    # ========================================================
    # LANGGRAPH CONFIG
    # ========================================================

    CONFIG = {

        "configurable": {

            "thread_id":
                current_thread_id

        },

        "metadata": {

            "thread_id":
                current_thread_id

        },

        "run_name":
            "chat_trace"

    }


    # ========================================================
    # ASSISTANT
    # ========================================================

    with st.chat_message(
        "assistant"
    ):

        status_holder = {

            "box": None

        }


        # ====================================================
        # AI STREAM
        # ====================================================

        def ai_stream():

            for (

                message_chunk,

                metadata

            ) in chatbot.stream(

                {

                    "messages": [

                        HumanMessage(

                            content=user_input

                        )

                    ]

                },

                config=CONFIG,

                stream_mode="messages"

            ):

                # --------------------------------------------
                # TOOL MESSAGE
                # --------------------------------------------

                if isinstance(

                    message_chunk,

                    ToolMessage

                ):

                    tool_name = getattr(

                        message_chunk,

                        "name",

                        "tool"

                    )


                    if status_holder[
                        "box"
                    ] is None:

                        status_holder[
                            "box"
                        ] = st.status(

                            f"🔧 Using `{tool_name}`...",

                            expanded=True

                        )


                    else:

                        status_holder[
                            "box"
                        ].update(

                            label=
                                f"🔧 Using `{tool_name}`...",

                            state="running",

                            expanded=True

                        )


                    continue


                # --------------------------------------------
                # AI MESSAGE
                # --------------------------------------------

                if isinstance(

                    message_chunk,

                    AIMessage

                ):

                    content = (
                        message_chunk.content
                    )


                    if (

                        isinstance(
                            content,
                            str
                        )

                        and

                        content

                    ):

                        yield content


            # =================================================
            # CHECK FOR INTERRUPT
            # =================================================

            pending_interrupt = (
                get_pending_interrupt(
                    current_thread_id
                )
            )


            if pending_interrupt is not None:

                save_pending_interrupt(

                    current_thread_id,

                    pending_interrupt

                )


        # ====================================================
        # STREAM RESPONSE
        # ====================================================

        ai_message = st.write_stream(
            ai_stream()
        )


        # ====================================================
        # TOOL STATUS
        # ====================================================

        if status_holder[
            "box"
        ] is not None:

            if get_pending_interrupt(
                current_thread_id
            ) is not None:

                status_holder[
                    "box"
                ].update(

                    label=
                        "⏸️ Waiting for human approval",

                    state="complete",

                    expanded=False

                )

            else:

                status_holder[
                    "box"
                ].update(

                    label=
                        "✅ Tool finished",

                    state="complete",

                    expanded=False

                )


    # ========================================================
    # SAVE AI MESSAGE
    # ========================================================

    if ai_message:

        st.session_state[
            "message_history"
        ].append({

            "role":
                "assistant",

            "content":
                ai_message

        })


    # ========================================================
    # UPDATE RECENT ACTIVITY
    # ========================================================

    update_chat_activity(
        current_thread_id
    )


    # ========================================================
    # CHECK HITL
    # ========================================================

    if (

        st.session_state.get(
            "pending_hitl"
        )

        is not None

        and

        st.session_state[
            "pending_hitl"
        ].get(
            "thread_id"
        )
        ==
        current_thread_id

    ):

        st.rerun()