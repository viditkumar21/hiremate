import json
from db import get_user, create_user, update_user

TOPIC_KEYWORDS = {
    "programming": ["recursion", "function", "variable", "loop"],
    "dsa": ["array", "linked list", "tree", "graph", "sort"],
    "networking": ["network", "protocol", "tcp", "udp", "ip"]
}

def detect_topic(message: str) -> str:
    msg_lower = message.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in msg_lower:
                return topic
    return "general"

def update_topic_tracking(user_id: str, message: str) -> None:
    # 1. Fetch User Data
    user = get_user(user_id)
    if user is None:
        create_user(user_id)
        user = get_user(user_id)
        if user is None:
            return  # Failsafe if DB cannot create user
            
    # 2. Extract Data (Safely handling dicts and strings just in case DB layer bypassed dict conversion)
    last_topics = user.get("last_topics") or {}
    if isinstance(last_topics, str):
        try:
            last_topics = json.loads(last_topics)
        except json.JSONDecodeError:
            last_topics = {}
            
    curiosity = user.get("curiosity") or {}
    if isinstance(curiosity, str):
        try:
            curiosity = json.loads(curiosity)
        except json.JSONDecodeError:
            curiosity = {}
            
    try:
        turn_count = int(user.get("turn_count") or 0)
    except ValueError:
        turn_count = 0
    
    # 3. Topic Detection
    detected_topic = detect_topic(message)
    last_topic = last_topics.get("current", "")
    
    # 4. Turn Count Logic
    if detected_topic == last_topic:
        turn_count += 1
    else:
        turn_count = 1  # Reset on topic change
        
    # 5. Curiosity Logic
    if turn_count > 3:
        current_curiosity = curiosity.get(detected_topic, 0)
        curiosity[detected_topic] = current_curiosity + 5
        
    # 6. Pack updates
    last_topics["current"] = detected_topic
    
    update_data = {
        "last_topics": last_topics,
        "turn_count": turn_count,
        "curiosity": curiosity
    }
    
    # 7. Persist via Database Helper
    update_user(user_id, update_data)


if __name__ == "__main__":
    test_user = "test_tracking_user"
    # Ensure fresh test baseline
    create_user(test_user)
    update_user(test_user, {"turn_count": 0, "last_topics": {}, "curiosity": {}})
    
    test_messages = [
        "What is recursion?",
        "Explain recursion again",
        "More on recursion",
        "Recursion examples",
        "What is TCP?"
    ]
    
    for idx, msg in enumerate(test_messages):
        print(f"\nProcessing Msg {idx+1}: '{msg}'")
        update_topic_tracking(test_user, msg)
        
        # Pull latest state to verify changes
        u = get_user(test_user)
        print(f" -> Topic: {u.get('last_topics', {}).get('current')}")
        print(f" -> Turn Count: {u.get('turn_count')}")
        print(f" -> Curiosity:  {u.get('curiosity')}")
