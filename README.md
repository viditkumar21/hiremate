# AI Tutor System

This project is an AI-powered tutor backend that goes beyond simple chat. It tracks user behavior, remembers past interactions, retrieves relevant knowledge from documents, and evaluates user understanding.

The system is designed to be fault-tolerant, meaning it continues working even if some components fail.

---

## Overview

The system combines multiple components:

* A language model (Groq LLM) for generating responses
* A short-term memory system for recent conversation
* A long-term user profile stored in a database
* A retrieval system (RAG) using a PDF and vector database
* A behavior tracking system (topics and curiosity)
* An evaluation module (Reality Check Mode)
* A LangGraph pipeline to orchestrate everything

---

## Features

### Chat System

The system responds to user queries using an LLM. It includes context from memory and retrieved knowledge to improve answers.

### Short-Term Memory

* Stores the last 6 messages per user
* After summarization, keeps only the last 4 messages
* Ensures memory does not grow indefinitely

### Long-Term User Data

Stored in SQLite:

* mastery (per topic)
* curiosity (interest level)
* chat summary
* last topic
* turn count

### Retrieval (RAG)

* Loads a PDF file
* Splits it into chunks
* Stores embeddings in ChromaDB
* Retrieves top 3 relevant chunks for a query

### Topic and Curiosity Tracking

* Detects topic using keywords
* Tracks repeated engagement with a topic
* Increases curiosity score when interest is high

### Reality Check Mode

* Triggered when user shows deep engagement (turn_count >= 5)
* Generates 3 questions
* Evaluates answers
* Assigns a score out of 100
* Updates mastery in database

### Fault Tolerance

The system is designed to never crash:

* LLM failure → returns fallback response
* DB failure → uses default user object
* RAG failure → uses empty context
* Invalid state → auto-corrected

---

## Tech Stack

* FastAPI (backend API)
* Groq LLM (llama3-8b-8192)
* SQLite (user database)
* ChromaDB (vector database)
* LangGraph (pipeline orchestration)
* Sentence Transformers (embeddings)
* PyPDF (PDF loading)

---

## Project Structure

```
project/
│
├── main.py
├── utils.py
├── db.py
├── memory.py
├── rag.py
├── tracking.py
├── evaluation.py
├── prompt_builder.py
├── requirements.txt
├── .env
└── chroma_db/
```

---

## Setup Instructions

1. Clone the repository

```
git clone <repo-url>
cd project
```

2. Create a virtual environment

```
python -m venv venv
source venv/bin/activate
```

3. Install dependencies

```
pip install -r requirements.txt
```

4. Create a `.env` file

```
GROQ_API_KEY=your_api_key_here
```

5. Run the server

```
uvicorn main:app --reload
```

---

## API Usage

Endpoint:

```
POST /chat
```

Request:

```json
{
  "user_id": "user1",
  "message": "Explain recursion"
}
```

Response:

```json
{
  "response": "Recursion is a function calling itself..."
}
```

---

## Testing

You should verify the following:

* Normal chat works correctly
* Repeated topics increase turn_count
* Reality Check Mode triggers after enough interaction
* RAG returns relevant content from the PDF

---

## Failure Handling Tests

* Break RAG (remove vector DB) → system still responds
* Break DB (rename users.db) → fallback user used
* Break LLM (invalid API key) → fallback message returned
* Pass invalid state → system recovers automatically

The system should never crash in any of these scenarios.

---

## How It Works

The request flow is:

User → FastAPI → LangGraph pipeline → LLM + DB + Memory + RAG → Response

Each step is isolated and protected with fallbacks to ensure stability.

---

## Notes

* The system is designed for learning and demonstration purposes
* It can be extended with a frontend or deployed to cloud
* Topic detection is keyword-based (can be improved later)

---

## Author

Chirag

---

## Final Remark

If all test cases pass and no failures break the system, this project represents a complete and robust AI backend suitable for portfolio and interviews.
