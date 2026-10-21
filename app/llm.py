"""LESSON 3 - LangChain: prompt -> model -> parser.

LangChain gives small composable building blocks:

  ChatPromptTemplate  builds the list of messages to send
  ChatOpenAI          the model wrapper (works w/ OpenRouter via base_url)
  StrOutputParser     turns the model's AIMessage into a plain str

They're joined with the `|` operator (LCEL - LangChain Expression
Language) into a "chain":

    chain = prompt | llm | parser
    chain.invoke({...})   # runs all three in order
"""
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from . import config

# The SYSTEM message sets the assistant's personality/rules.
# This version reduces hallucination by asking the model to be honest
# and avoid inventing facts.
SYSTEM_PROMPT = (
    "You are a helpful and honest AI teaching assistant. "
    "Answer clearly and accurately. "
    "Do not invent facts, dates, names, statistics, or examples. "
    "If you are unsure, say 'I am not certain' and explain what needs to be checked."
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        # Placeholder gets replaced by the whole chat history (list of messages)
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)


def build_chain():
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Copy .env.example to .env and add your key."
        )
    llm = ChatOpenAI(
        model=config.OPENROUTER_MODEL,
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,  # <- the whole OpenRouter trick
        temperature=0.7,  # 0 = deterministic, 1+ = more creative
        timeout=60,
        max_retries=2,
    )
    return prompt | llm | StrOutputParser()


_chain = None


def get_chain():
    """Build once, reuse (lazy so the server can start without a key)."""
    global _chain
    if _chain is None:
        _chain = build_chain()
    return _chain


def to_lc_messages(rows: list[dict]):
    """Convert DB rows -> LangChain message objects."""
    return [
        HumanMessage(r["content"]) if r["role"] == "user" else AIMessage(r["content"])
        for r in rows
    ]


def ask(question: str, history_rows: list[dict]) -> str:
    return get_chain().invoke(
        {"question": question, "history": to_lc_messages(history_rows)}
    )
