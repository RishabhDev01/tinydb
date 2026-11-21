"""A minimal tool-calling agent loop over Groq (ADR-005).

The agent ends by calling ``finish``. Its arguments are the agent's output
(a spec, a design, a summary or a verdict). The orchestrator never trusts
the claim; it runs its own checks (ADR-007).
"""
import json

from .llm import chat, log, strip_think
from .tools import ToolError, clip

NUDGE = ("Continue. Use the tools to work, and call the `finish` tool "
         "when you are done. Do not reply with plain text only.")


class AgentStopped(Exception):
    pass


def _compact(messages: list, max_chars: int) -> None:
    """Drop old tool outputs once the context gets large (Groq TPM limits)."""
    def size():
        return sum(len(str(m.get("content") or "")) for m in messages)
    for m in messages[2:-6]:
        if size() <= max_chars:
            return
        if m.get("role") == "tool" and not m["content"].startswith("[old"):
            m["content"] = "[old tool output removed to save tokens]"


def run_agent(*, role: str, model: str, messages: list, tools: list,
              impl: dict, finish_schema: dict, max_turns: int,
              budget: int, max_chars: int = 24000,
              max_tokens: int = 4096) -> dict:
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
        msg = chat(role, model, messages, tools=all_tools, budget=budget,
                   max_tokens=max_tokens)
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
                             "content": clip(str(result), limit=12000)})
    raise AgentStopped(f"{role}: reached max_turns={max_turns} "
                       "without calling finish")
