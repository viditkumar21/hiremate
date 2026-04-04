from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pipeline import app_pipeline
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str

@app.get("/")
async def index():
    return FileResponse("index.html")

@app.post("/chat")
async def chat(req: ChatRequest):
    logging.info(f"API called | user_id={req.user_id} | message={req.message}")
    try:
        result = app_pipeline.invoke({
            "user_id": req.user_id,
            "message": req.message
        })
        return {
            "response": result.get("response", "No response")
        }
    except Exception:
        return {
            "response": "System error. Please try again later."
        }
