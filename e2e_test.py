"""
End-to-end system verification for the AI Tutor pipeline.
Tests: normal chat, topic continuity, test mode, RAG, and failure resilience.
"""
import os, sys, shutil
from unittest.mock import MagicMock
from db import get_user, create_user, update_user
from pipeline import app_pipeline

PASS = "\u2705 PASS"
FAIL = "\u274c FAIL"
SEP  = "\n" + "="*60
results = []

def invoke(user_id, message):
    return app_pipeline.invoke({"user_id": user_id, "message": message})

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    print(f"  {status} {label}" + (f" | {detail}" if detail else ""))
    results.append(condition)
    return condition

# ─────────────────────────────────────────────────────────────
# TEST 1: Normal chat
# ─────────────────────────────────────────────────────────────
print(SEP)
print("TEST 1: Normal chat")
uid = "e2e_t1"
create_user(uid)
out = invoke(uid, "What is a variable in Python?")
check("Returns response key",     "response" in out)
check("Response is non-empty",    len(out.get("response", "")) > 0)
check("Mode is teach",            out.get("mode") == "teach")

# ─────────────────────────────────────────────────────────────
# TEST 2: Same topic repeated → turn_count increases
# ─────────────────────────────────────────────────────────────
print(SEP)
print("TEST 2: Turn count increments on same topic")
uid = "e2e_t2"
create_user(uid)
update_user(uid, {"turn_count": 0, "last_topics": {}, "curiosity": {}})

for msg in ["What is recursion?", "Explain recursion again", "More on recursion please"]:
    invoke(uid, msg)

user_after = get_user(uid)
tc   = user_after.get("turn_count", 0)
topic = user_after.get("last_topics", {}).get("current", "")
check("turn_count > 1 after repeated topic", tc > 1,       f"turn_count={tc}")
check("Topic detected as programming",       topic == "programming", f"topic={topic}")

# ─────────────────────────────────────────────────────────────
# TEST 3: Trigger test mode (turn_count >= 5)
# ─────────────────────────────────────────────────────────────
print(SEP)
print("TEST 3: Test mode activates when turn_count >= 5")
uid = "e2e_t3"
create_user(uid)
update_user(uid, {"turn_count": 5, "last_topics": {"current": "programming"}})
out = invoke(uid, "recursion calls itself")
check("Mode is test",              out.get("mode") == "test",  f"mode={out.get('mode')}")
check("Response non-empty",        len(out.get("response", "")) > 0)

# ─────────────────────────────────────────────────────────────
# TEST 4: RAG — PDF context retrieved
# ─────────────────────────────────────────────────────────────
print(SEP)
print("TEST 4: RAG retrieves PDF context")
uid = "e2e_t4"
create_user(uid)
out = invoke(uid, "Tell me about Python learning")
ctx = out.get("retrieved_context", None)
check("retrieved_context key exists",        ctx is not None)
check("retrieved_context is string",         isinstance(ctx, str))
check("RAG context non-empty (PDF hit)",     len(ctx) > 0,  f"len={len(ctx)}")

# ─────────────────────────────────────────────────────────────
# TEST 5a: RAG failure
# ─────────────────────────────────────────────────────────────
print(SEP)
print("TEST 5a: RAG failure — pipeline resilience")
if os.path.exists("chroma_db"):
    shutil.move("chroma_db", "chroma_db_bak")
try:
    uid = "e2e_t5a"
    create_user(uid)
    out = invoke(uid, "What is recursion?")
    check("No crash on RAG failure",              "response" in out)
    check("retrieved_context is empty fallback",  out.get("retrieved_context") == "")
finally:
    if os.path.exists("chroma_db_bak"):
        shutil.move("chroma_db_bak", "chroma_db")

# ─────────────────────────────────────────────────────────────
# TEST 5b: DB failure
# ─────────────────────────────────────────────────────────────
print(SEP)
print("TEST 5b: DB failure — pipeline resilience")
if os.path.exists("users.db"):
    shutil.move("users.db", "users.db.bak")
try:
    out = invoke("e2e_t5b", "What is a loop?")
    check("No crash on DB failure",           "response" in out)
    check("Response non-empty without DB",    len(out.get("response", "")) > 0)
finally:
    if os.path.exists("users.db.bak"):
        shutil.move("users.db.bak", "users.db")

# ─────────────────────────────────────────────────────────────
# TEST 5c: LLM failure
# ─────────────────────────────────────────────────────────────
print(SEP)
print("TEST 5c: LLM failure — pipeline resilience")
import utils as utils_module
real_client = utils_module.client

mock_client = MagicMock()
mock_client.chat.completions.create.side_effect = Exception("Simulated LLM timeout")
utils_module.client = mock_client

try:
    uid = "e2e_t5c"
    create_user(uid)
    out = invoke(uid, "What is a function?")
    resp = out.get("response", "")
    check("No crash on LLM failure",        "response" in out)
    check("Returns safe fallback message",  "Temporary issue" in resp, f"got='{resp[:60]}'")
finally:
    utils_module.client = real_client

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
print(SEP)
passed = sum(results)
total  = len(results)
print(f"\nRESULT: {passed}/{total} checks passed")
if passed == total:
    print("\u2705 All end-to-end tests PASSED. System is fully stable.")
else:
    print(f"\u274c {total - passed} check(s) FAILED. Review output above.")
    sys.exit(1)
