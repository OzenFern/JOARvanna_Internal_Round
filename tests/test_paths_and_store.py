from datetime import datetime, timezone
from inspect import signature
from pathlib import Path

from blackbox.capture.schema import AgentStep, AgentTrace, StepType, TaskType
from blackbox.capture.store import TraceStore
from blackbox.faults.labels import LABELS_PATH, LabelStore
from blackbox.paths import ARTIFACTS_DIR, PROJECT_ROOT, REPORTS_DIR, TRACES_DIR
from scripts.export_report import export
from scripts.run_analysis import analyze
from scripts.run_eval import evaluate
from scripts.train_local import train


def _trace(run_id: str = "test-run") -> AgentTrace:
    now = datetime.now(timezone.utc)
    step = AgentStep(
        step_index=0,
        step_type=StepType.LLM_CALL,
        timestamp=now,
        latency_ms=1.5,
        inputs={"prompt": "2 + 2"},
        output="4",
    )
    return AgentTrace(
        run_id=run_id,
        task_id="test-task",
        task_type=TaskType.MATH,
        task_description="Calculate 2 + 2",
        steps=[step],
        final_output="4",
        expected_output="4",
        success=True,
        started_at=now,
        ended_at=now,
    )


def test_project_data_paths_are_independent_of_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert PROJECT_ROOT == Path(__file__).resolve().parents[1]
    assert TRACES_DIR == PROJECT_ROOT / "data" / "traces"
    assert TRACES_DIR != tmp_path / "data" / "traces"


def test_trace_store_round_trips_trace_in_custom_directory(tmp_path):
    store = TraceStore(tmp_path / "traces")
    trace = _trace()

    saved_path = store.save(trace)
    loaded = store.load(trace.run_id)

    assert saved_path == tmp_path / "traces" / "test-run.json"
    assert store.list_runs() == ["test-run"]
    assert loaded.run_id == trace.run_id
    assert loaded.task_type is TaskType.MATH
    assert loaded.steps[0].output == "4"
    assert loaded.success is True


def test_default_stores_use_project_data_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    trace_store = TraceStore()
    label_store = LabelStore()

    assert trace_store.traces_dir == TRACES_DIR
    assert label_store.path == LABELS_PATH
    assert LABELS_PATH == ARTIFACTS_DIR / "labels.json"


def test_all_canonical_data_directories_are_under_project_root():
    for path in (TRACES_DIR, ARTIFACTS_DIR, REPORTS_DIR):
        assert path.is_relative_to(PROJECT_ROOT)


def test_cli_helpers_default_to_canonical_project_paths():
    export_params = signature(export).parameters
    analyze_params = signature(analyze).parameters
    evaluate_params = signature(evaluate).parameters
    train_params = signature(train).parameters

    assert export_params["traces_dir"].default == TRACES_DIR
    assert export_params["output_file"].default == REPORTS_DIR / "report.md"
    assert analyze_params["traces_dir"].default == TRACES_DIR
    assert analyze_params["model_path"].default == ARTIFACTS_DIR / "model.pkl"
    assert evaluate_params["traces_dir"].default == TRACES_DIR
    assert evaluate_params["model_path"].default == ARTIFACTS_DIR / "model.pkl"
    assert train_params["traces_dir"].default == TRACES_DIR
    assert train_params["labels_file"].default == ARTIFACTS_DIR / "labels.json"
    assert train_params["output_model"].default == ARTIFACTS_DIR / "model.pkl"
