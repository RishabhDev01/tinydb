"""A minimal tool-calling agent loop over Groq (ADR-005).

The agent ends by calling ``finish``. Its arguments are the agent's output
(a spec, a design, a summary or a verdict). The orchestrator never trusts
the claim; it runs its own checks (ADR-007).
"""
import json

from .llm import RequestTooLarge, chat, log, strip_think
from .tools import ToolError, clip

NUDGE = ("Continue. Use the tools to work, and call the `finish` tool "
         "when you are done. Do not reply with plain text only.")


class AgentStopped(Exception):
    pass


def _size(messages: list) -> int:
    n = 0
    for m in messages:
        n += len(str(m.get("content") or ""))
        for c in m.get("tool_calls") or []:
            n += len(c["function"]["arguments"])
    return n


def _compact(messages: list, max_chars: int, keep_last: int = 6) -> None:
    """Shrink the context to fit Groq's per-request TPM limit (ADR-013).

    1. replace old tool outputs with a stub (oldest first);
    2. if still too big, shorten old tool-call arguments (e.g. whole files
       passed to write_file, or earlier drafts passed to finish);
    3. if still too big, cut recent tool outputs to 1,500 characters.
    """
    stub = "[old tool output removed to save tokens]"
    end = len(messages) - keep_last
    for m in messages[2:max(2, end)]:
        if _size(messages) <= max_chars:
            return
        if m.get("role") == "tool" and m["content"] != stub:
            m["content"] = stub
    for m in messages[2:max(2, end)]:
        if _size(messages) <= max_chars:
            return
        for c in m.get("tool_calls") or []:
            if len(c["function"]["arguments"]) > 400:
                c["function"]["arguments"] = '{"note": "[arguments ' \
                    'removed to save tokens]"}'
    for m in messages[2:]:
        if _size(messages) <= max_chars:
            return
        if m.get("role") == "tool" and len(m["content"]) > 1500:
            m["content"] = m["content"][:1500] + "\n[... truncated]"


def run_agent(*, role: str, model: str, messages: list, tools: list,
              impl: dict, finish_schema: dict, max_turns: int,
              budget: int, max_chars: int = 15000,
              max_tokens: int = 1800) -> dict:
    """Run until the model calls finish. Returns finish's arguments.

    ``messages`` is modified in place, so the caller can continue the same
    conversation later (the builder does this on a retry).
    """
    finish_tool = {"type": "function", "function": {
        "name": "finish",
        "description": "Call exactly once when your work is complete.",
        "parameters": finish_schema}}
    all_tools = tools + [finish_tool]
    nudges = 0
    for turn in range(1, max_turns + 1):
        _compact(messages, max_chars)
        limit, keep = max_chars, 6
        for shrink in range(4):
            try:
                msg = chat(role, model, messages, tools=all_tools,
                           budget=budget, max_tokens=max_tokens)
                break
            except RequestTooLarge:
                if shrink == 3:
                    raise
                limit, keep = int(limit * 0.65), max(0, keep - 2)
                log(f"{role}: 413 request too large, compacting to "
                    f"{limit} chars (keep_last={keep})")
                _compact(messages, limit, keep_last=keep)
        calls = msg.tool_calls or []
        entry = {"role": "assistant", "content": strip_think(msg.content)}
        if calls:
            entry["tool_calls"] = [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name,
                              "arguments": c.function.arguments or "{}"}}
                for c in calls]
        messages.append(entry)

        if not calls:
            nudges += 1
            if nudges > 3:
                raise AgentStopped(f"{role}: no tool calls after 3 nudges")
            messages.append({"role": "user", "content": NUDGE})
            continue

        for c in calls:
            name = c.function.name
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError as e:
                result = f"ERROR: arguments are not valid JSON: {e}"
                args = None
            if args is not None and name == "finish":
                log(f"{role}: finish after {turn} turns")
                # Answer any other pending tool calls so the transcript
                # stays valid if this conversation is continued.
                answered = {m.get("tool_call_id") for m in messages
                            if m.get("role") == "tool"}
                for other in calls:
                    if other.id not in answered:
                        messages.append({"role": "tool",
                                         "tool_call_id": other.id,
                                         "content": "ok"})
                return args
            if args is not None:
                fn = impl.get(name)
                if fn is None:
                    result = f"ERROR: unknown tool {name!r}"
                else:
                    try:
                        result = fn(**args)
                    except ToolError as e:
                        result = f"ERROR: {e}"
                    except TypeError as e:
                        result = f"ERROR: bad arguments: {e}"
            log(f"{role}: turn {turn} {name}({str(args)[:80]})")
            messages.append({"role": "tool", "tool_call_id": c.id,
                             "content": clip(str(result), limit=5000)})
    raise AgentStopped(f"{role}: reached max_turns={max_turns} "
                       "without calling finish")
