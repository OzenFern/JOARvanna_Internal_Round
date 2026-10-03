"""
blackbox/attribution/baselines/cloud_judge.py
─────────────────────────────────────────────
External LLM as a judge.
"""
from __future__ import annotations
import json
import httpx
from blackbox.capture.schema import AgentTrace

class CloudJudge:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        
    async def predict(self, trace: AgentTrace) -> dict[int, float]:
        steps = "\n".join(f"Step {s.step_index} [{s.tool or s.step_type}]: in={s.inputs} out={s.output}" 
                         for s in trace.steps)
        prompt = (
            f"Task: {trace.task_description}\n"
            f"Expected: {trace.expected_output}\n"
            f"Observed: {trace.final_output}\n\n"
            f"Steps:\n{steps}\n\n"
            "Identify the faulty step index. Reply with ONLY JSON: {\"fault_step\": <int>, \"confidence\": <float_0_to_1>}"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )
            resp.raise_for_status()
            data = json.loads(resp.json()["choices"][0]["message"]["content"])
            idx = int(data.get("fault_step", -1))
            conf = float(data.get("confidence", 1.0))
            return {i: conf if i == idx else 0.0 for i in range(len(trace.steps))}
