import pytest
import os
import json
from scripts.generate_report import generate_benchmark_metrics, write_json_report, write_markdown_report

@pytest.mark.asyncio
async def test_generate_report_payload():
    data = await generate_benchmark_metrics()
    assert "metadata" in data
    assert "tasks" in data
    assert data["metadata"]["passed_tasks"] == data["metadata"]["total_tasks"]
    assert data["metadata"]["pass_rate_pct"] == 100.0
    assert len(data["tasks"]) >= 3

def test_report_file_export(tmp_path):
    sample_data = {
        "metadata": {
            "timestamp": "2026-08-22T00:00:00Z",
            "engine": "Test Engine",
            "total_tasks": 1,
            "passed_tasks": 1,
            "pass_rate_pct": 100.0,
            "average_trajectory_efficiency": 0.89
        },
        "tasks": [{
            "task_id": "TEST_001",
            "domain": "testing",
            "description": "Test Task",
            "status": "PASSED",
            "max_steps": 3,
            "tolerance": 1e-3,
            "trajectory_efficiency": 0.89,
            "invariants_verified": ["metric_a"],
            "step_reward_history": [0.7, 0.95, 0.9]
        }]
    }

    json_path = os.path.join(tmp_path, "report.json")
    md_path = os.path.join(tmp_path, "report.md")

    write_json_report(sample_data, json_path)
    write_markdown_report(sample_data, md_path)

    assert os.path.exists(json_path)
    assert os.path.exists(md_path)

    with open(json_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
        assert loaded["metadata"]["engine"] == "Test Engine"

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Replica Benchmark Performance Report" in content
        assert "TEST_001" in content
