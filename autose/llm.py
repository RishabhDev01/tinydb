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



class LLMError(Exception):
    pass


class BudgetExceeded(Exception):
    pass


class RequestTooLarge(LLMError):
    """HTTP 413: one request is larger than the model's tokens-per-minute
    limit (8,000 for gpt-oss-120b on the free tier; see ADR-013)."""


class QuotaExhausted(LLMError):
    """A 429 asked us to wait longer than LONG_WAIT_S: the model's daily
    quota is used up and no fallback model is left (ADR-015)."""


# ADR-015: a per-minute limit never asks for more than ~60 s. A longer
# retry-after means the daily quota is spent (run 44942070537 slept 15-28
# min per call until the job timed out). Then we switch to a fallback model
# with its own quota, or stop at once with a clear reason.
LONG_WAIT_S = float(os.environ.get("AUTOSE_LONG_WAIT_S", "90"))
# ADR-019: Gemini (paid) first, then Groq's free gpt-oss models.
_DEFAULT_FALLBACK = ("gemini-3.8-flash>openai/gpt-oss-120b,"
                     "openai/gpt-oss-120b>openai/gpt-oss-20b")
FALLBACK = dict(pair.split(">", 1) for pair in os.environ.get(
    "AUTOSE_FALLBACK", _DEFAULT_FALLBACK).split(",") if ">" in pair)
_EXHAUSTED: dict = {}  # model -> seconds Groq asked us to wait


def _route(model: str) -> str | None:
    """The model to call: ``model`` or its first fallback with quota left."""
    seen = set()
    while model in _EXHAUSTED:
        if model in seen:
            return None
        seen.add(model)
        model = FALLBACK.get(model)
        if model is None:
            return None
    return model


# Reasoning settings per model family. Hidden reasoning tokens count
# towards max_tokens and TPM, so keep them low (ADR-013). If a model rejects
# the parameter, we drop it and remember that.
REASONING = {"openai/gpt-oss": {"reasoning_effort": "low"},
             "gemini-": {"reasoning_effort": "low"},
             "qwen/": {"reasoning_effort": "none"}}
_NO_REASONING_PARAM: set = set()


def log(msg: str) -> None:
    print(f"[autose] {msg}", file=sys.stderr, flush=True)


# ADR-019: two OpenAI-compatible providers. A model name says which one:
# "gemini-..." goes to Google (paid Tier 1), everything else to Groq.
PROVIDERS = {
    "groq": (GROQ_BASE_URL, "GROQ_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/",
               "GEMINI_API_KEY"),
}
_clients: dict = {}


def provider(model: str) -> str:
    return "gemini" if model.startswith("gemini") else "groq"


def _get_client(model: str = "") -> OpenAI:
    name = provider(model)
    if name not in _clients:
        base_url, key_env = PROVIDERS[name]
        _clients[name] = OpenAI(base_url=base_url,
                                api_key=os.environ[key_env],
                                timeout=180, max_retries=0)
    return _clients[name]


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
    parse_failures = 0
    requested = model
    while True:
        attempt += 1
        model = _route(requested)
        if model is None:
            waits = ", ".join(f"{m} ~{w / 60:.0f} min"
                              for m, w in _EXHAUSTED.items())
            raise QuotaExhausted(f"{role}: Groq daily quota used up for "
                                 f"{requested} and its fallbacks "
                                 f"(retry after: {waits})")
        try:
            kwargs = dict(model=model, messages=messages,
                          max_tokens=max_tokens,
                          temperature=temperature + 0.2 * parse_failures)
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            extra = next((v for k, v in REASONING.items()
                          if model.startswith(k)), None)
            if extra and model not in _NO_REASONING_PARAM:
                kwargs["extra_body"] = extra
            resp = _get_client(model).chat.completions.create(**kwargs)
            break
        except RateLimitError as e:
            wait = _retry_after(e) or min(60, 2 ** attempt) + random.random()
            if wait > LONG_WAIT_S:
                _EXHAUSTED[model] = wait
                nxt = _route(requested)
                log(f"{role}: 429 on {model} asks for {wait:.0f}s, so its "
                    f"quota is spent; "
                    + (f"falling back to {nxt}" if nxt else "no fallback")
                    + f" | {str(e)[:220]}")
                attempt = 0
                continue
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
            # The model wrote something Groq could not parse into a message
            # or tool call (e.g. gpt-oss emitting its reasoning as the
            # answer; seen in run 44938351640). Sampling again usually
            # works; after two failures, also drop the reasoning setting.
            if e.status_code == 400 and ("tool_use_failed" in body or
                                         "output_parse_failed" in body):
                parse_failures += 1
                if parse_failures > 4:
                    raise LLMError(f"{role}: model output unparseable "
                                   f"{parse_failures} times: {body[:400]}") \
                        from e
                if parse_failures >= 2 and model not in _NO_REASONING_PARAM:
                    log(f"{role}: dropping reasoning params for {model}")
                    _NO_REASONING_PARAM.add(model)
                log(f"{role}: unparseable output ({parse_failures}), "
                    "resampling")
                continue
            if e.status_code == 400 and "reasoning_effort" in body and \
                    model not in _NO_REASONING_PARAM:
                log(f"{role}: {model} rejects reasoning params; dropping")
                _NO_REASONING_PARAM.add(model)
                continue
            if e.status_code >= 500 and attempt <= MAX_RETRIES:
                time.sleep(min(30, 2 ** attempt))
                continue
            raise LLMError(f"{role}: HTTP {e.status_code}: {body[:500]}") \
                from e

    u = USAGE.setdefault(role, {"prompt": 0, "completion": 0, "calls": 0})
    if model != requested:
        u.setdefault("fallback_calls", {})
        u["fallback_calls"][model] = u["fallback_calls"].get(model, 0) + 1
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
