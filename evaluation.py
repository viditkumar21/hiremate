import json
import re
from db import get_user, create_user, update_user
from utils import call_llm

def get_current_topic(user) -> str:
    last_topics = user.get("last_topics") or {}
    if isinstance(last_topics, str):
        try:
            last_topics = json.loads(last_topics)
        except json.JSONDecodeError:
            last_topics = {}
    return last_topics.get("current", "general")

def generate_questions(user_id: str) -> list[str]:
    user = get_user(user_id)
    if not user:
        create_user(user_id)
        user = get_user(user_id)
        if not user:
            return []
            
    topic = get_current_topic(user)
    
    prompt = (
        f"Generate exactly 3 short questions to test understanding of the topic '{topic}'. "
        "Return ONLY the questions separated by newlines. No introductory context or numbering is needed."
    )
    
    try:
        response = call_llm(prompt)
        if response.startswith("Error"):
            return []
            
        questions = [q.strip() for q in response.split("\n") if q.strip()]
        
        # Strip any accidental numbers that the LLM ignored formatting rules for
        cleaned = []
        for q in questions:
            q = re.sub(r'^\d+[\.\)]\s*', '', q)
            cleaned.append(q)
            
        return cleaned[:3]
    except Exception:
        return []

def evaluate_answers(user_id: str, questions: list, answers: list) -> int:
    qa_text = ""
    for q, a in zip(questions, answers):
        qa_text += f"Q: {q}\nA: {a}\n\n"
        
    prompt = (
        "Evaluate the correctness of the following answers based on their corresponding questions.\n"
        "Return ONLY a single integer number between 0 and 100 representing the total score. Do not write anything else.\n\n"
        f"{qa_text}"
    )
    
    try:
        response = call_llm(prompt)
        matches = re.findall(r'\d+', response)
        if matches:
            # e.g., if response is "85/100", matches[0] is "85"
            score = int(matches[0])
            return max(0, min(100, score))
        return 0
    except Exception:
        return 0

def update_mastery(user_id: str, score: int) -> None:
    user = get_user(user_id)
    if not user:
        return
        
    topic = get_current_topic(user)
    
    mastery = user.get("mastery") or {}
    if isinstance(mastery, str):
        try:
            mastery = json.loads(mastery)
        except json.JSONDecodeError:
            mastery = {}
            
    mastery[topic] = score
    update_user(user_id, {"mastery": mastery})

def run_reality_check(user_id: str, answers: list[str]) -> int:
    # 1. Fetch user
    user = get_user(user_id)
    if not user:
        create_user(user_id)
        user = get_user(user_id)
        if not user:
            return -1
            
    # 2. Check turn_count
    try:
        turn_count = int(user.get("turn_count") or 0)
    except ValueError:
        turn_count = 0
        
    # 3. Guard constraints
    if turn_count < 5:
        return -1
        
    # 4. Generate questions
    questions = generate_questions(user_id)
    if not questions:
        return 0
        
    # 5. Evaluate answers
    score = evaluate_answers(user_id, questions, answers)
    
    # 6. Update DB
    update_mastery(user_id, score)
    
    # 7. Return score
    return score

if __name__ == "__main__":
    test_user = "test_eval_user"
    create_user(test_user)
    
    # Pre-configure conditions to assert against logic blocks
    update_user(test_user, {
        "turn_count": 5,
        "last_topics": {"current": "programming"}, 
        "mastery": {}
    })
    
    print("\n--- Testing Reality Check Evaluation System ---")
    mock_answers = [
        "A function that calls itself.", 
        "Variables declared inside the function body.",
        "To stop infinite recursive loops."
    ]
    
    final_score = run_reality_check(test_user, mock_answers)
    
    print(f"Evaluated Score: {final_score}")
    
    final_user_blob = get_user(test_user)
    print(f"DB Output for Mastery: {final_user_blob.get('mastery')}")
