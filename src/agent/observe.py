"""Agent observability: turn logs, tool traces, loop detection.

Per agentic-AI best practice: log every LLM call (prompt, output,
tokens, latency, model) and trace the tool-call chain so demos and
debugging can show *why* the agent decided what it did.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

LOOP_REPEAT_THRESHOLD = 3  # same tool+args N times = stuck


class TurnLog:
    """One agent turn: prompt, output, metrics, and tool-call trace."""

    def __init__(self, prompt: str, model: str):
        self.prompt = prompt
        self.model = model
        self.output = None
        self.stop_reason = None
        self.input_tokens = 0
        self.output_tokens = 0
        self.latency_ms = 0.0
        self.tool_calls = []
        self.started = datetime.now(timezone.utc).isoformat()

    def record_tool(self, tool: str, args: dict, result, ok: bool,
                    latency_ms: float = 0.0):
        self.tool_calls.append({
            "tool": tool,
            "args": args,
            "ok": ok,
            "latency_ms": latency_ms,
            "result_preview": str(result)[:200],
        })

    def finish(self, output, stop_reason, input_tokens: int,
               output_tokens: int, latency_ms: float):
        self.output = output
        self.stop_reason = stop_reason
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.latency_ms = latency_ms

    def has_loop(self) -> bool:
        """Detect the agent calling the same tool with identical args
        repeatedly — a stuck loop that should be broken."""
        seen = {}
        for tc in self.tool_calls:
            key = (tc["tool"], json.dumps(tc["args"], sort_keys=True))
            seen[key] = seen.get(key, 0) + 1
            if seen[key] >= LOOP_REPEAT_THRESHOLD:
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "started": self.started,
            "model": self.model,
            "prompt": self.prompt,
            "output": self.output,
            "stop_reason": self.stop_reason,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "tool_calls": self.tool_calls,
        }


class ObservingCallbackHandler:
    """Strands callback handler that traces tool calls into a TurnLog.

    Also streams text output like PrintingCallbackHandler, so the REPL
    keeps its live streaming UX while events are captured.
    """

    def __init__(self, turn_log: TurnLog, stream: bool = True):
        self._log = turn_log
        self._stream = stream
        self._current_tool = None
        self._tool_start = None
        self._result_text = []

    def __call__(self, **kwargs):
        event = kwargs.get("event", {}) or {}

        # tool call start: contentBlockStart.start.toolUse {name, input}
        tool_use = (
            event.get("contentBlockStart", {}).get("start", {}).get("toolUse")
        )
        if tool_use:
            self._current_tool = {
                "tool": tool_use.get("name", "?"),
                "args": tool_use.get("input", {}) or {},
            }
            self._tool_start = time.monotonic()
            self._result_text = []

        # tool result: {toolName, content}
        tool_result = kwargs.get("tool_result") or (
            event.get("contentBlockStop", {}).get("tool_result")
            if isinstance(event, dict) else None
        )
        if tool_result and self._current_tool:
            self._flush_tool_call(ok=True)

        # streamed text
        data = kwargs.get("data", "")
        if data and self._stream:
            print(data, end="" if not kwargs.get("complete") else "\n")

        # capture tool result text from reason events if present
        if kwargs.get("reasoningText") and self._stream:
            pass  # reasoning noise — skip

    def _flush_tool_call(self, ok: bool):
        if not self._current_tool:
            return
        latency = (time.monotonic() - (self._tool_start or time.monotonic())) * 1000
        self._log.record_tool(
            self._current_tool["tool"],
            args=self._current_tool["args"],
            result=" ".join(self._result_text)[:200] or "(no captured result)",
            ok=ok,
            latency_ms=latency,
        )
        self._current_tool = None
        self._tool_start = None


class AgentLogger:
    """Collects TurnLogs; optionally persists as JSONL."""

    def __init__(self, log_dir: str = None):
        self._entries = []
        self._log_dir = Path(log_dir) if log_dir else None
        if self._log_dir:
            self._log_dir.mkdir(parents=True, exist_ok=True)

    def add(self, turn: TurnLog):
        self._entries.append(turn)
        if self._log_dir:
            log_file = self._log_dir / "agent_log.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps(turn.to_dict()) + "\n")

    def entries(self) -> list:
        return list(self._entries)

    def summary(self) -> dict:
        return {
            "turns": len(self._entries),
            "total_input_tokens": sum(t.input_tokens for t in self._entries),
            "total_output_tokens": sum(t.output_tokens for t in self._entries),
            "total_tool_calls": sum(len(t.tool_calls) for t in self._entries),
        }
