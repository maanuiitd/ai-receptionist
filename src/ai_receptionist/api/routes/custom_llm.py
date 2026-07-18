"""Vapi custom-llm endpoint: OpenAI-compatible streaming /chat/completions.

Step 1: canned/proxy replies to verify plumbing.
Later: swap the generator for graph.builder invocation.
"""

import json
import time
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ai_receptionist.config import settings

router = APIRouter()


# --- SSE framing (OpenAI streaming dialect) --------------------------------

def _chunk(chunk_id: str, created: int, delta: dict, finish_reason=None) -> str:
    payload = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": settings.llm_model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(payload)}\n\n"


# --- Reply generators (replaced by the LangGraph graph in step 2) ----------

async def _canned_reply(messages):
    last_user = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
        "",
    )
    text = (
        f"I heard you say: {last_user}. The custom L L M server is connected."
        if last_user
        else "The custom L L M server is connected and streaming correctly."
    )
    for word in text.split(" "):
        yield word + " "


async def _openai_reply(messages):
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        stream=True,
        # temperature=0.7,
    )
    async for event in stream:
        if event.choices and event.choices[0].delta.content:
            yield event.choices[0].delta.content


# --- Endpoint ---------------------------------------------------------------

@router.post("/chat/completions")
async def chat_completions(request: Request):
    if (
        settings.vapi_webhook_secret
        and request.headers.get("x-vapi-secret") != settings.vapi_webhook_secret
    ):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    body = await request.json()
    messages = body.get("messages", [])
    call_id = (body.get("call") or {}).get("id", "no-call-id")
    print(f"[{call_id}] turn, {len(messages)} messages")

    gen = (
        _openai_reply(messages)
        if settings.openai_api_key
        else _canned_reply(messages)
    )
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    async def event_stream():
        yield _chunk(chunk_id, created, {"role": "assistant", "content": ""})
        async for token in gen:
            yield _chunk(chunk_id, created, {"content": token})
        yield _chunk(chunk_id, created, {}, finish_reason="stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )