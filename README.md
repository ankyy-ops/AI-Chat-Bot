# AI Teacher Chat — FastAPI + LangChain + SQLite + OpenRouter (free)

A learning project. Read the lessons in order, then run it.

## 0. Big picture

```
Browser ──HTTP──> FastAPI ──> SQLite (load history)
                     │
                     └──> LangChain chain ──> OpenRouter (free LLM)
                     │
                     └──> SQLite (save question + answer)
```

| File | Lesson | Job |
|---|---|---|
| `app/config.py` | 1 | Load secrets from `.env` |
| `app/database.py` | 2 | SQLite tables + CRUD |
| `app/llm.py` | 3 | LangChain prompt → model → parser |
| `app/main.py` | 4 | FastAPI endpoints |
| `static/index.html` | 5 | Tiny chat UI |

## 1. Setup (Windows PowerShell)

```powershell
cd "C:\Users\Ankit Yadav\ai-chat-teacher"
python -m venv .venv                 # isolated Python env for this project
.\.venv\Scripts\Activate.ps1         # activate it (prompt shows (.venv))
pip install -r requirements.txt
copy .env.example .env               # then edit .env and paste your key
uvicorn app.main:app --reload        # start server
```

Open http://127.0.0.1:8000 (chat) and http://127.0.0.1:8000/docs (auto API docs).

**Free key:** sign up at https://openrouter.ai → Keys → Create. Models ending
in `:free` cost nothing (rate-limited, ~20 req/min, ~50/day without credits).
If `.ps1` activation is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## 2. Concepts, deep dive

### Why a virtual environment?
Each project gets its own package versions, so projects don't break each other.

### Why `.env`?
Keys in code leak via git. `.env` is local and git-ignored. `load_dotenv()`
copies it into `os.environ`.

### LLMs are stateless
The model remembers nothing. Every request must contain the whole
conversation. SQLite stores messages; each turn we load the last 20 and send
them again. That *is* "memory". Bigger history = more tokens = slower/costlier,
hence `MAX_HISTORY`.

### Message roles
- `system` — rules/personality (set once by you)
- `human`/`user` — what the student says
- `ai`/`assistant` — what the model said

### LangChain / LCEL
`prompt | llm | parser` pipes output of each step into the next, like a shell
pipe. `chain.invoke(dict)` runs it. Each piece is swappable: change
`ChatOpenAI` to another provider and nothing else changes. `MessagesPlaceholder`
injects a list of past messages into the prompt.

### Why `ChatOpenAI` for OpenRouter?
OpenRouter copies OpenAI's API shape. Same client, different `base_url`.

### SQLite essentials
- One file, zero server. `sqlite3` is built into Python.
- `?` placeholders prevent SQL injection.
- `PRIMARY KEY`, `REFERENCES` model "a conversation has many messages".
- Context manager commits on success / rolls back on error.
- Inspect it: `sqlite3 chat.db "select * from messages;"` or DB Browser for SQLite.

### FastAPI essentials
- Decorator `@app.post("/chat")` maps URL + method to a function.
- Pydantic `ChatRequest` validates JSON; wrong shape → automatic 422.
- `async def` + `run_in_threadpool` — the LLM call blocks, so push it to a
  thread so the server stays responsive.
- `HTTPException` returns clean error codes (404 not found, 502 upstream failed).
- `lifespan` runs startup code (create tables).

## 3. Try it from the command line

```powershell
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"What is an API?\"}"
```
Use the returned `conversation_id` in the next call for follow-ups.

## 4. Exercises (do these to really learn)

1. Edit `SYSTEM_PROMPT` to make the bot a pirate; observe the change.
2. Set `MAX_HISTORY = 2` and see the bot "forget" earlier context.
3. Add `GET /health` returning `{"ok": true}`.
4. Add a `subject` field to `ChatRequest` and inject it into the system prompt.
5. Stream tokens: use `chain.astream(...)` + `StreamingResponse`.
6. Replace raw `sqlite3` with SQLAlchemy.
7. Add summarization: when history > 20 messages, summarize old ones.

## 5. Troubleshooting

| Symptom | Cause |
|---|---|
| 500 "OPENROUTER_API_KEY is missing" | `.env` not created / wrong folder |
| 502 with 401 | Bad key |
| 502 with 429 | Free rate limit; wait a minute |
| 502 with 404 model | Free model renamed; set `OPENROUTER_MODEL=openrouter/free` |
