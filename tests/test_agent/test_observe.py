"""Tests for agent observability: turn logs with tool traces and metrics."""
import time

from src.agent.observe import TurnLog, AgentLogger


def test_turnlog_records_basics():
    log = TurnLog(prompt="hello", model="test-model")
    log.finish(output="world", stop_reason="end_turn",
              input_tokens=10, output_tokens=5, latency_ms=120.0)
    assert log.prompt == "hello"
    assert log.output == "world"
    assert log.input_tokens == 10
    assert log.output_tokens == 5
    assert log.stop_reason == "end_turn"
    assert log.latency_ms == 120.0


def test_turnlog_tool_calls_traced():
    log = TurnLog(prompt="scan", model="m")
    log.record_tool("scan_documents", args={"path": "data/samples"},
                    result="4 tasks...", ok=True)
    assert len(log.tool_calls) == 1
    tc = log.tool_calls[0]
    assert tc["tool"] == "scan_documents"
    assert tc["ok"] is True
    assert tc["latency_ms"] >= 0


def test_turnlog_tool_error_recorded():
    log = TurnLog(prompt="x", model="m")
    log.record_tool("boom", args={}, result="Error: bad", ok=False)
    assert log.tool_calls[0]["ok"] is False


def test_agent_logger_appends_and_serializes(tmp_path):
    logger = AgentLogger(log_dir=str(tmp_path))
    log = TurnLog(prompt="p", model="m")
    log.record_tool("t", args={}, result="r", ok=True)
    log.finish(output="o", stop_reason="end_turn",
              input_tokens=1, output_tokens=2, latency_ms=5.0)
    logger.add(log)
    entries = logger.entries()
    assert len(entries) == 1
    d = log.to_dict()
    assert d["prompt"] == "p"
    assert d["tool_calls"][0]["tool"] == "t"


def test_agent_logger_persists_jsonl(tmp_path):
    logger = AgentLogger(log_dir=str(tmp_path))
    log = TurnLog(prompt="persist me", model="m")
    log.finish(output="done", stop_reason="end_turn",
              input_tokens=3, output_tokens=4, latency_ms=9.0)
    logger.add(log)

    import json
    log_file = tmp_path / "agent_log.jsonl"
    assert log_file.exists()
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["prompt"] == "persist me"


def test_loop_detection():
    logger = AgentLogger()
    log = TurnLog(prompt="p", model="m")
    # same tool, same args, three times = loop
    for _ in range(3):
        log.record_tool("search_documents", args={"query": "x"}, result="r", ok=True)
    assert log.has_loop() is True

    log2 = TurnLog(prompt="p", model="m")
    log2.record_tool("a", args={"x": 1}, result="r", ok=True)
    log2.record_tool("a", args={"x": 2}, result="r", ok=True)  # different args
    log2.record_tool("a", args={"x": 1}, result="r", ok=True)  # x=1 now twice
    log2.record_tool("b", args={"x": 1}, result="r", ok=True)  # different tool
    # max repeat is 2, under threshold — no loop
    assert log2.has_loop() is False
