import json
from db import get_user, create_user, update_user
from utils import call_llm

MAX_MESSAGES = 6          # Hard cap: never store more than 6 messages
MAX_AFTER_SUMMARY = 4     # After LLM summary: keep only last 4

memory_store = {}

def add_message(user_id: str, message: dict) -> None:
    if user_id not in memory_store:
        memory_store[user_id] = []
    memory_store[user_id].append(message)
    # Hard cap: trim oldest messages if over limit
    if len(memory_store[user_id]) > MAX_MESSAGES:
        memory_store[user_id] = memory_store[user_id][-MAX_MESSAGES:]

def get_messages(user_id: str) -> list:
    return memory_store.get(user_id, [])

def process_memory(user_id: str, message: str) -> None:
    """
    1. Add message
    2. Check trigger
    3. Call LLM if needed
    4. Update DB
    5. Trim memory
    """
    # Auto-create user if they don't exist
    try:
        user = get_user(user_id)
        if user is None:
            create_user(user_id)
    except Exception:
        pass # Do not crash on DB error

    # 1. Add message
    add_message(user_id, {"role": "user", "content": message})
    
    # 2. Check trigger
    messages = get_messages(user_id)
    if len(messages) >= 8:
        # 3. Call LLM
        combined = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        prompt = (
            "Please analyze the following conversation and generate a structured summary. "
            "Highlight the following areas:\n"
            "1. topics (what user is learning)\n"
            "2. strengths\n"
            "3. weak areas\n"
            "4. mistakes\n"
            "Keep the output concise, clear, and structured.\n\n"
            f"Conversation:\n{combined}"
        )
        
        try:
            summary = call_llm(prompt)
            # 4. Update DB
            if summary and not summary.startswith("Error"):
                update_user(user_id, {"chat_summary": summary})
        except Exception:
            pass # Do not crash if LLM or DB fails
            
        # 5. Trim memory (keep ONLY last MAX_AFTER_SUMMARY messages, preserve order)
        memory_store[user_id] = messages[-MAX_AFTER_SUMMARY:]

if __name__ == "__main__":
    test_user = "test_memory_overflow"

    create_user(test_user)
    update_user(test_user, {"chat_summary": ""})

    print("--- Sending 20 messages ---")
    for i in range(1, 21):
        process_memory(test_user, f"Message {i}")
        count = len(get_messages(test_user))
        print(f"  After msg {i:02d}: memory size = {count}")
        assert count <= MAX_MESSAGES, f"OVERFLOW at msg {i}: size={count} > {MAX_MESSAGES}"

    final = get_messages(test_user)
    print(f"\nFinal memory size: {len(final)} (must be <= {MAX_MESSAGES})")
    print(f"Final messages: {[m['content'] for m in final]}")
    assert len(final) <= MAX_MESSAGES, "FAIL: Memory exceeded hard cap!"
    print("\nAll assertions passed. Memory is always bounded. ✅")
