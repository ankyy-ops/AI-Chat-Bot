"""LESSON 4 - FastAPI: the web layer.

FastAPI turns Python functions into HTTP endpoints. Pydantic models
validate request bodies automatically (bad input -> 422 error for free),
and interactive docs appear at /docs.

Request flow for POST /chat:
  1. validate body            (Pydantic)
  2. create/load conversation (SQLite)
  3. load past messages       (SQLite)  <- the "memory"
  4. call the LLM chain       (LangChain -> OpenRouter)
  5. save user + AI messages  (SQLite)
  6. return the reply
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import database as db
from . import llm

MAX_HISTORY = 20  # only send the last N messages to the model (cost/limits)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()  # runs once at startup
    yield


app = FastAPI(title="AI Teacher Chat", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None  # omit to start a new conversation


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if req.conversation_id:
        if not db.conversation_exists(req.conversation_id):
            raise HTTPException(404, "Conversation not found")
        conv_id = req.conversation_id
    else:
        conv_id = db.create_conversation(title=req.message)

    history = db.get_messages(conv_id, limit=MAX_HISTORY)

    try:
        # llm.ask is blocking (network call). run_in_threadpool keeps the
        # async server responsive for other users while we wait.
        reply = await run_in_threadpool(llm.ask, req.message, history)
    except RuntimeError as e:  # missing API key
        raise HTTPException(500, str(e))
    except Exception as e:  # rate limit, model down, etc.
        raise HTTPException(502, f"LLM error: {e}")

    # Save only after success so failed calls don't leave half a turn.
    db.add_message(conv_id, "user", req.message)
    db.add_message(conv_id, "assistant", reply)
    return ChatResponse(conversation_id=conv_id, reply=reply)


@app.get("/conversations")
def conversations():
    return db.list_conversations()


@app.get("/conversations/{conv_id}")
def conversation(conv_id: str):
    if not db.conversation_exists(conv_id):
        raise HTTPException(404, "Conversation not found")
    return db.get_messages(conv_id)


@app.delete("/conversations/{conv_id}")
def delete(conv_id: str):
    db.delete_conversation(conv_id)
    return {"deleted": conv_id}


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent.parent / "static" / "index.html")
