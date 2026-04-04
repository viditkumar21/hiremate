from typing import Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

# Local module imports
from db import get_user, create_user, update_user
from memory import process_memory, get_messages
from tracking import update_topic_tracking
from rag import retrieve_context
from prompt_builder import build_prompt
from evaluation import generate_questions, evaluate_answers, update_mastery
from utils import call_llm
import logging

class TutorState(TypedDict, total=False):
    user_id: str
    message: str
    user: dict
    memory: list
    retrieved_context: str
    prompt: str
    mode: str
    response: str
    score: int
    questions: list

def validate_state(state: dict) -> dict:
    if not isinstance(state, dict):
        state = {}
    state["user_id"]  = state.get("user_id",  "default_user")
    state["message"]  = state.get("message",  "")
    state["user"]     = state.get("user",     {})
    state["memory"]   = state.get("memory",   [])
    state["retrieved_context"] = state.get("retrieved_context", "")
    state["prompt"]   = state.get("prompt",   "")
    state["mode"]     = state.get("mode",     "teach")
    state["response"] = state.get("response", "")
    state["score"]    = state.get("score",    0)
    state["questions"]= state.get("questions",[])
    logging.info(f"Validated state keys: {list(state.keys())}")
    return state

def log_transition(node_name: str, state: TutorState = None):
    logging.info(f"Node: {node_name}")
    if state:
        logging.info(f"State: {state}")

def node_input(state: TutorState):
    state = validate_state(state)
    log_transition("input", state)
    return state

def node_load_user(state: TutorState):
    state = validate_state(state)
    log_transition("load_user", state)
    user_id = state.get("user_id", "")
    try:
        user = get_user(user_id)
        if not user:
            create_user(user_id)
            user = get_user(user_id)
            if not user:
                raise Exception("User not found after creation")
    except Exception as e:
        logging.error(f"Fallback load_user: {e}")
        user = {
            "user_id": user_id,
            "mastery": {},
            "curiosity": {},
            "chat_summary": "",
            "last_topics": {},
            "turn_count": 0,
            "last_updated": ""
        }
    return {"user": user}

def node_memory(state: TutorState):
    state = validate_state(state)
    log_transition("memory", state)
    user_id = state.get("user_id", "")
    message = state.get("message", "")
    try:
        process_memory(user_id, message)
        msgs = get_messages(user_id)
    except Exception as e:
        logging.error(f"Fallback memory: {e}")
        msgs = []
    return {"memory": msgs}

def node_topic(state: TutorState):
    state = validate_state(state)
    log_transition("topic", state)
    user_id = state.get("user_id", "")
    message = state.get("message", "")
    try:
        update_topic_tracking(user_id, message)
        user = get_user(user_id)
        if not user:
            raise Exception("Topic tracking get_user fail")
    except Exception as e:
        logging.error(f"Fallback topic: {e}")
        user = state.get("user", {
            "user_id": user_id,
            "mastery": {},
            "curiosity": {},
            "chat_summary": "",
            "last_topics": {},
            "turn_count": 0,
            "last_updated": ""
        })
    return {"user": user}

def node_rag(state: TutorState):
    state = validate_state(state)
    log_transition("rag", state)
    query = state.get("message", "")
    try:
        context_list = retrieve_context(query)
        context = "\n".join(context_list) if context_list else ""
    except Exception:
        context = ""
        
    return {"retrieved_context": context}

def node_decide(state: TutorState):
    state = validate_state(state)
    log_transition("decide", state)
    try:
        user = state.get("user", {})
        tc = int(user.get("turn_count") or 0)
        mode = "test" if tc >= 5 else "teach"
    except Exception as e:
        logging.error(f"Fallback decide: {e}")
        mode = "teach"
    return {"mode": mode}

def router_mode(state: TutorState):
    return state.get("mode", "teach")

def node_teach(state: TutorState):
    state = validate_state(state)
    log_transition("teach", state)
    try:
        prompt = build_prompt(state["user_id"], state["message"])
    except Exception as e:
        logging.error(f"Fallback teach: {e}")
        prompt = ""
    return {"prompt": prompt}

def node_test(state: TutorState):
    state = validate_state(state)
    log_transition("test", state)
    try:
        questions = generate_questions(state["user_id"])
    except Exception as e:
        logging.error(f"Fallback test: {e}")
        questions = []
    return {"questions": questions}

def node_generate(state: TutorState):
    state = validate_state(state)
    log_transition("generate", state)
    mode = state.get("mode", "teach")
    try:
        if mode == "teach":
            resp = call_llm(state.get("prompt", ""))
            if not resp or resp.startswith("Error"):
                resp = "Error generating response"
        else:
            qs = state.get("questions", [])
            resp = "\n".join(qs) if qs else "Error generating test questions"
    except Exception as e:
        logging.error(f"Fallback generate: {e}")
        resp = "Error generating response"
    return {"response": resp}

def node_evaluate(state: TutorState):
    state = validate_state(state)
    log_transition("evaluate", state)
    try:
        qs = state.get("questions", [])
        ans = [state.get("message", "Dummy Answer")] * len(qs)
        score = evaluate_answers(state["user_id"], qs, ans)
    except Exception as e:
        logging.error(f"Fallback evaluate: {e}")
        score = 0
    return {"score": score}

def node_update(state: TutorState):
    state = validate_state(state)
    log_transition("update", state)
    try:
        mode = state.get("mode")
        if mode == "test" and state.get("score") is not None:
            try:
                update_mastery(state["user_id"], state["score"])
            except Exception:
                pass  # Silently ignore DB update failure
    except Exception as e:
        logging.error(f"Fallback update: {e}")
    return {}

def node_response(state: TutorState):
    state = validate_state(state)
    log_transition("response", state)
    return {}


# Build Graph
workflow = StateGraph(TutorState)

workflow.add_node("input", node_input)
workflow.add_node("load_user", node_load_user)
workflow.add_node("memory", node_memory)
workflow.add_node("topic", node_topic)
workflow.add_node("rag", node_rag)
workflow.add_node("decide", node_decide)
workflow.add_node("teach", node_teach)
workflow.add_node("test", node_test)
workflow.add_node("generate", node_generate)
workflow.add_node("evaluate", node_evaluate)
workflow.add_node("update", node_update)
workflow.add_node("response", node_response)

workflow.add_edge(START, "input")
workflow.add_edge("input", "load_user")
workflow.add_edge("load_user", "memory")
workflow.add_edge("memory", "topic")
workflow.add_edge("topic", "rag")
workflow.add_edge("rag", "decide")

workflow.add_conditional_edges(
    "decide",
    router_mode,
    {"teach": "teach", "test": "test"}
)

workflow.add_edge("teach", "generate")
workflow.add_edge("test", "generate")

def route_after_generate(state: TutorState):
    return state.get("mode", "teach")

workflow.add_conditional_edges(
    "generate",
    route_after_generate,
    {"teach": "update", "test": "evaluate"} 
)

workflow.add_edge("evaluate", "update")
workflow.add_edge("update", "response")
workflow.add_edge("response", END)

app_pipeline = workflow.compile()

if __name__ == "__main__":
    test_user = "pipeline_user_v7"
    
    print("\n--- Running TEACH flow ---")
    state_in = {"user_id": test_user, "message": "What is recursion?"}
    out_1 = app_pipeline.invoke(state_in)
    print("\n---> Result TEACH mode:", out_1.get("mode"))
    
    print("\n--- Triggering TEST mode (simulating > 5 messages) ---")
    update_user(test_user, {"turn_count": 5, "last_topics": {"current": "programming"}})
    
    state_in_test = {"user_id": test_user, "message": "recursion calls itself"}
    out_all = app_pipeline.invoke(state_in_test)
    
    print("\n---> Result mode:", out_all.get("mode"))
    print("---> Evaluated Score:", out_all.get("score"))

