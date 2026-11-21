"""Groq chat client with rate-limit backoff and per-role token accounting.

ADR-005: Groq's OpenAI-compatible endpoint, used through the ``openai`` client.
ADR-009: 429s are expected on the free tier, so we back off, honouring
``retry-after``, and give up after MAX_RETRIES.
"""
import json
import os
import random
import re
import sys
import time

from openai import (APIConnectionError, APIStatusError, APITimeoutError,
                    OpenAI, RateLimitError)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MAX_RETRIES = int(os.environ.get("AUTOSE_MAX_RETRIES", "10"))

# role -> {"prompt": int, "completion": int, "calls": int}
USAGE: dict = {}

_client = None


class LLMError(Exception):
    pass


class BudgetExceeded(Exception):
    pass


class RequestTooLarge(LLMError):
    """HTTP 413: one request is larger than the model's tokens-per-minute
    limit (8,000 for gpt-oss-120b on the free tier; see ADR-013)."""


# Reasoning settings per model family. Hidden reasoning tokens count
# towards max_tokens and TPM, so keep them low (ADR-013). If a model rejects
# the parameter, we drop it and remember that.
REASONING = {"openai/gpt-oss": {"reasoning_effort": "low"},
             "qwen/": {"reasoning_effort": "none"}}
_NO_REASONING_PARAM: set = set()


def log(msg: str) -> None:
    print(f"[autose] {msg}", file=sys.stderr, flush=True)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=GROQ_BASE_URL,
                         api_key=os.environ["GROQ_API_KEY"],
                         timeout=180, max_retries=0)
    return _client


def _retry_after(err) -> float | None:
    try:
        value = err.response.headers.get("retry-after")
        return float(value) + 0.5 if value else None
    except Exception:
        return None


def total_tokens(role: str) -> int:
    u = USAGE.get(role, {})
    return u.get("prompt", 0) + u.get("completion", 0)


def chat(role: str, model: str, messages: list, tools: list | None = None,
         max_tokens: int = 1800, budget: int | None = None,
         temperature: float = 0.2):
    """One chat completion. Returns the message object."""
    attempt = 0
    while True:
        attempt += 1
        try:
            kwargs = dict(model=model, messages=messages,
                          max_tokens=max_tokens, temperature=temperature)
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            extra = next((v for k, v in REASONING.items()
                          if model.startswith(k)), None)
            if extra and model not in _NO_REASONING_PARAM:
                kwargs["extra_body"] = extra
            resp = _get_client().chat.completions.create(**kwargs)
            break
        except RateLimitError as e:
            wait = _retry_after(e) or min(60, 2 ** attempt) + random.random()
            if attempt > MAX_RETRIES:
                raise LLMError(f"{role}: still rate-limited after "
                               f"{MAX_RETRIES} retries: {e}") from e
            log(f"{role}: 429 rate limited, sleeping {wait:.1f}s "
                f"(retry {attempt}/{MAX_RETRIES})")
            time.sleep(wait)
        except (APIConnectionError, APITimeoutError) as e:
            if attempt > MAX_RETRIES:
                raise LLMError(f"{role}: connection failed: {e}") from e
            time.sleep(min(30, 2 ** attempt))
        except APIStatusError as e:
            body = str(getattr(e, "body", "")) + str(e)
            if e.status_code == 413:
                raise RequestTooLarge(f"{role}: HTTP 413: {body[:300]}") \
                    from e
            if e.status_code == 400 and "reasoning" in body and \
                    model not in _NO_REASONING_PARAM:
                log(f"{role}: {model} rejects reasoning params; dropping")
                _NO_REASONING_PARAM.add(model)
                continue
            # Malformed tool call from the model: sampling again often works.
            if e.status_code == 400 and "tool_use_failed" in body \
                    and attempt <= 2:
                log(f"{role}: tool_use_failed, resampling")
                continue
            if e.status_code >= 500 and attempt <= MAX_RETRIES:
                time.sleep(min(30, 2 ** attempt))
                continue
            raise LLMError(f"{role}: HTTP {e.status_code}: {body[:500]}") \
                from e

    u = USAGE.setdefault(role, {"prompt": 0, "completion": 0, "calls": 0})
    if resp.usage:
        u["prompt"] += resp.usage.prompt_tokens or 0
        u["completion"] += resp.usage.completion_tokens or 0
    u["calls"] += 1
    if budget and total_tokens(role) > budget:
        raise BudgetExceeded(f"{role} used {total_tokens(role)} tokens, "
                             f"budget {budget}")
    return resp.choices[0].message


def strip_think(text: str | None) -> str:
    """Remove <think>...</think> blocks some reasoning models emit."""
    if not text:
        return ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def extract_json(text: str):
    """Parse the first JSON object in ``text`` (tolerates code fences)."""
    text = strip_think(text)
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    candidates = [fence.group(1)] if fence else []
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for c in candidates:
        try:
            return json.loads(c)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"no JSON object found in: {text[:300]!r}")
