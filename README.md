# 🤖 Agentic AI Chatbot with LangGraph

An intelligent, multi-tool conversational AI agent built with **LangGraph** and **Streamlit**. The chatbot can reason, call tools, retrieve information from documents, and pause for human approval before taking sensitive actions — all with persistent, multi-threaded chat history.

## 🚀 Live Demo

https://multi-agent-chatbot-system-wqnzj8tevcsfhmusymimps.streamlit.app

## ✨ Features

- **Conversational Agent** — powered by Groq's `openai/gpt-oss-20b` model via LangGraph
- **Multi-Tool Reasoning** — the agent decides when to use:
  - 🌐 **Web Search** (Tavily) — for current events and real-time information
  - 🧮 **Calculator** — for mathematical expressions
  - 📈 **Stock Price Lookup** (Alpha Vantage) — fetches live stock quotes
  - 🌤️ **Weather Lookup** (OpenWeather) — real-time weather by city
  - 📄 **RAG over PDFs** (FAISS + Gemini Embeddings) — upload a PDF and ask questions about it
- **Human-in-the-Loop (HITL)** — stock purchase actions pause execution and require explicit human approval (✅ Approve / ❌ Reject) before continuing
- **Persistent Multi-Chat Threads** — each conversation is saved with a unique thread ID, auto-generated title, and full history via SQLite checkpointing
- **Streaming Responses** — assistant replies stream token-by-token in the UI, with live status indicators while tools are running

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Orchestration | LangGraph |
| LLM | Groq (`openai/gpt-oss-20b`) |
| UI | Streamlit |
| Vector Store | FAISS |
| Embeddings | Google Generative AI (Gemini) |
| Conversation Memory | SQLite (`langgraph-checkpoint-sqlite`) |
| Web Search | Tavily |
| Stock Data | Alpha Vantage |
| Weather Data | OpenWeather |

## 📁 Project Structure

```
├── app.py                              # Streamlit frontend — chat UI, threads, HITL controls
├── agentic_chatbot_backend.py          # Basic chatbot graph (no tools)
├── agentic_chatbot_db_backend.py       # Chatbot graph with SQLite persistence
├── agentic_chatbot_tool_backend.py     # Chatbot graph with tool-calling (search, calc, stock, weather)
├── agentic_chatbot_rag_backend.py      # Adds RAG (PDF Q&A) on top of tool-calling
├── agentic_chatbot_hitl_backend.py     # Full version: tools + RAG + human-in-the-loop approval
├── requirements.txt                    # Python dependencies
└── .gitignore                          # Excludes venv, .env, databases, and cache files
```

## ⚙️ Setup & Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/mzaid4696-bot/multi-agent-chatbot-system.git
   cd multi-agent-chatbot-system
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # Mac/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   Create a `.env` file in the project root with:
   ```
   GROQ_API_KEY=your_groq_api_key
   TAVILY_API_KEY=your_tavily_api_key
   OPENWEATHER_API_KEY=your_openweather_api_key
   GOOGLE_API_KEY=your_google_api_key
   ```

   > ⚠️ Never commit your `.env` file — it's already excluded via `.gitignore`.

5. **Run the app**
   ```bash
   streamlit run app.py
   ```

## 🧠 How It Works

The agent uses a LangGraph state machine with conditional routing:

1. User sends a message
2. The LLM decides whether to answer directly or call a tool
3. If a tool is needed (search, calculator, stock, weather, or PDF retrieval), it's executed and the result is fed back to the LLM
4. For stock purchases specifically, execution **pauses** via `interrupt()` and waits for human approval before completing
5. The final response streams back to the user, and the conversation state is checkpointed to SQLite for persistence across sessions

## 📌 Notes

- The `agentic_chatbot_hitl_backend.py` is the most complete backend and is the one actually used by `app.py`
- The other backend files (`agentic_chatbot_backend.py`, `_db_backend.py`, `_tool_backend.py`, `_rag_backend.py`) represent incremental development stages of the project
