from db import get_user
from memory import get_messages
from rag import retrieve_context

def build_prompt(user_id: str, query: str) -> str:
    # 1. Fetch chat_summary (Fallback to empty string if missing or error)
    chat_summary = ""
    try:
        user = get_user(user_id)
        if user and user.get("chat_summary"):
            chat_summary = user["chat_summary"]
    except Exception:
        pass

    # 2. Fetch short-term memory (preserve order)
    recent_messages = []
    try:
        msgs = get_messages(user_id)
        if msgs:
            for m in msgs:
                # Format: role: content
                role = m.get("role", "user")
                content = m.get("content", "")
                recent_messages.append(f"{role}: {content}")
    except Exception:
        pass

    # 3. Retrieve context via RAG
    relevant_chunks = []
    try:
        relevant_chunks = retrieve_context(query)
    except Exception:
        pass

    # Formatting Helpers
    def format_list(items):
        if not items:
            return ""
        return "\n".join([f"- {str(item).strip()}" for item in items])

    recent_formatted = format_list(recent_messages)
    chunks_formatted = format_list(relevant_chunks)

    # 4. Strict Formatting Structure
    # Note: Sections must still exist even if empty
    prompt = f"""You are a strict AI tutor.

Student Profile:
{chat_summary}

Recent Conversation:
{recent_formatted}

Relevant Study Material:
{chunks_formatted}

Current Question:
{query}

Instructions:
- Answer clearly
- Focus on weak areas
- Do not give unnecessary information"""

    # MANDATORY: Log/print before sending to LLM
    print("====== GENERATED HYBRID PROMPT ======\n")
    print(prompt)
    print("\n=====================================")

    return prompt

if __name__ == "__main__":
    from memory import add_message
    # Seed the in-memory dictionary temporarily so we can test list formatting
    add_message("test_user_summarization", {"role": "user", "content": "What is Python?"})
    add_message("test_user_summarization", {"role": "assistant", "content": "Python is a programming language."})
    
    # Test script enforcing correct structure output
    # Relies on test_user existing in DB, having recent memory logs, and test DB having RAG loaded
    output = build_prompt("test_user_summarization", "What is recursion?")
