# Blackbox Core Module Documentation

This document provides detailed implementation details for the core `blackbox` library, which handles trace capture, fault attribution, analysis, and debugging.

## Table of Contents

- [Capture Module](#capture-module)
- [Attribution Module](#attribution-module)
- [Analysis Module](#analysis-module)
- [Features Module](#features-module)
- [Agents Module](#agents-module)
- [Faults Module](#faults-module)
- [Replay Module](#replay-module)
- [Debug Module](#debug-module)
- [Explain Module](#explain-module)
- [Compare Module](#compare-module)
- [Evaluate Module](#evaluate-module)

---

## Capture Module

The capture module (`blackbox/capture/`) provides the foundational data structures and instrumentation for recording agent executions.

### Schema (`schema.py`)

Defines the core data structures that represent agent execution traces.

#### Key Classes

**StepType (Enum)**
```python
class StepType(str, Enum):
    LLM_CALL    = "llm_call"      # LLM model invocation
    TOOL_CALL   = "tool_call"     # External tool execution
    OBSERVATION = "observation"   # Result observation
    DECISION    = "decision"      # Agent decision point
    RETRIEVAL   = "retrieval"     # Document/data retrieval
```

**TaskType (Enum)**
```python
class TaskType(str, Enum):
    QA       = "qa"              # Question answering
    TEXT2SQL = "text2sql"        # Text-to-SQL generation
    MATH     = "math"            # Mathematical reasoning
    CUSTOM   = "custom"          # Custom task type
```

**TokenUsage (Dataclass)**
```python
@dataclass
class TokenUsage:
    input_tokens:  int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
```

**AgentError (Dataclass)**
```python
@dataclass
class AgentError:
    error_type: str                 # e.g., "ToolError", "ValidationError"
    message:    str
    traceback:  str | None = None
```

**ToolCall (Dataclass)**
```python
@dataclass
class ToolCall:
    tool_name:  str                 # Name of the tool executed
    arguments:  dict[str, Any]      # Arguments passed to tool
    result:     Any                 # Tool execution result
    latency_ms: float               # Execution time in milliseconds
    error:      AgentError | None = None  # Error if tool failed
```

**ModelCall (Dataclass)**
```python
@dataclass
class ModelCall:
    model:      str                 # Model identifier (e.g., "gpt-4")
    prompt:     str | list[dict]    # Prompt text or chat messages
    response:   str                 # Model response
    tokens:     TokenUsage          # Token consumption
    latency_ms: float               # Inference latency
```

**AgentStep (Dataclass)**
```python
@dataclass
class AgentStep:
    step_index:    int              # Position in execution sequence
    step_type:     StepType         # Type of step
    timestamp:     datetime         # When step occurred
    latency_ms:    float            # Step execution time
    inputs:        dict[str, Any]   # Step inputs
    output:        Any              # Step output
    tool:          str | None       # Tool name if applicable
    tool_call:     ToolCall | None  # Detailed tool telemetry
    model_call:    ModelCall | None # Detailed model telemetry
    error:         AgentError | None # Error if step failed
    tokens:        TokenUsage | None # Token usage
    checkpoint_id: str | None       # Associated checkpoint ID
    metadata:      dict[str, Any]  # Additional metadata
    step_id:       str              # Unique step identifier (UUID)

    @property
    def has_error(self) -> bool:
        return self.error is not None

    @property
    def name(self) -> str:
        """Short display name for this step."""
        if self.tool:
            return f"{self.tool}()"
        return self.step_type.value
```

**Checkpoint (Dataclass)**
```python
@dataclass
class Checkpoint:
    checkpoint_id: str              # Unique checkpoint identifier
    step_index:    int              # Step index where checkpoint was taken
    state:         dict[str, Any]   # Serializable agent state
    timestamp:     datetime         # When checkpoint was created
```

**AgentTrace (Dataclass)**
```python
@dataclass
class AgentTrace:
    run_id:          str              # Unique run identifier
    task_id:         str              # Task identifier
    task_type:       TaskType         # Domain of the task
    task_description: str             # Human-readable task description
    steps:           list[AgentStep]  # Sequence of execution steps
    final_output:    Any              # Final agent output
    expected_output: Any              # Expected correct output
    success:         bool             # Whether execution succeeded
    started_at:      datetime         # Execution start time
    ended_at:        datetime         # Execution end time
    error:           AgentError | None # Top-level error if any
    fault_type:      str | None       # Ground truth fault type (for training)
    fault_step:      int | None       # Ground truth fault step (for training)
    meta:            dict[str, Any]   # Additional metadata

    @property
    def n_steps(self) -> int:
        return len(self.steps)

    @property
    def total_latency_ms(self) -> float:
        return sum(s.latency_ms for s in self.steps)

    @property
    def total_tokens(self) -> int:
        return sum(s.tokens.total_tokens for s in self.steps if s.tokens)

    @property
    def error_steps(self) -> list[AgentStep]:
        return [s for s in self.steps if s.has_error]

    def step(self, index: int) -> AgentStep:
        return self.steps[index]
```

### Instrumentation (`instrument.py`)

Provides observability hooks for recording agent executions.

#### TraceContext

The main context manager for recording agent traces.

```python
class TraceContext:
    """Context manager that accumulates steps and builds a finished AgentTrace."""

    def __init__(self, run_id: str | None = None, task_id: str | None = None):
        self.run_id  = run_id or str(uuid.uuid4())[:12]
        self.task_id = task_id or str(uuid.uuid4())[:8]
        self._steps: list[AgentStep] = []
        self._started_at = _now()

    @contextmanager
    def step(
        self,
        step_type: StepType | str,
        *,
        tool: str | None = None,
        inputs: dict | None = None,
    ) -> Generator[StepRecorder, None, None]:
        """Record a single step in the execution."""
        # Creates a StepRecorder, yields it for the user to set output/error
        # Automatically appends the built step to the trace on exit

    def build_trace(
        self,
        *,
        task_type: TaskType,
        task_description: str,
        expected_output: Any,
        final_output: Any,
        success: bool,
        fault_type: str | None = None,
        fault_step: int | None = None,
        meta: dict | None = None,
    ) -> AgentTrace:
        """Build the final AgentTrace from accumulated steps."""
```

**Usage Example:**
```python
with TraceContext(run_id="run-01", task_id="math-42") as ctx:
    with ctx.step("llm_call", tool=None) as step:
        response = llm.call(prompt)
        step.set_output(response)
        step.set_model_call("gpt-4", prompt, response, 50, 20)
    
    with ctx.step("tool_call", tool="calculator") as step:
        result = calculator(expression)
        step.set_output(result)
        step.set_tool_call("calculator", {"expression": expression}, result)

trace = ctx.build_trace(
    task_type=TaskType.MATH,
    task_description="Solve 2+2",
    expected_output=4,
    final_output=result,
    success=(result == 4)
)
```

#### StepRecorder

Mutable builder for a single AgentStep, used inside a `with ctx.step(...)` block.

```python
class StepRecorder:
    def set_output(self, value: Any) -> None:
        """Set the step output."""

    def set_error(self, error_type: str, message: str, tb: str | None = None) -> None:
        """Record an error that occurred during this step."""

    def set_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Set token usage for this step."""

    def set_model_call(self, model: str, prompt: Any, response: str,
                       input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Record LLM model call details."""

    def set_tool_call(self, tool_name: str, arguments: dict, result: Any,
                      error: str | None = None) -> None:
        """Record tool execution details."""

    def set_meta(self, **kwargs) -> None:
        """Add custom metadata to the step."""
```

#### @capture_tool Decorator

Decorator that automatically wraps tool functions and records their calls.

```python
def capture_tool(tool_name: str, ctx_attr: str = "_trace_ctx"):
    """
    Decorator that wraps a tool function and records its call into a TraceContext.
    The TraceContext must be attached to `self` (or the first arg) as `ctx_attr`.
    """
```

**Usage Example:**
```python
class Agent:
    def __init__(self):
        self._trace_ctx = TraceContext(run_id="run-01")

    @capture_tool("calculator")
    def calculate(self, expression: str) -> float:
        return eval(expression)

# When calculate() is called, it's automatically recorded in self._trace_ctx
```

### Store (`store.py`)

Handles persistence and retrieval of AgentTrace objects.

#### TraceStore

```python
class TraceStore:
    def __init__(self, traces_dir: Path = TRACES_DIR):
        """Initialize store with traces directory (creates if needed)."""

    def save(self, trace: AgentTrace) -> Path:
        """Save a trace as JSON file (returns file path)."""

    def load(self, run_id: str) -> AgentTrace:
        """Load a trace by run_id (raises FileNotFoundError if not found)."""

    def load_all(self) -> list[AgentTrace]:
        """Load all traces from the traces directory."""

    def list_runs(self) -> list[str]:
        """List all available run_ids."""

    def save_batch(self, traces: list[AgentTrace]) -> None:
        """Save multiple traces at once."""

    def export_pkl(self, path: Path) -> None:
        """Export all traces as pickle for fast ML loading."""

    @staticmethod
    def load_pkl(path: Path) -> list[AgentTrace]:
        """Load traces from pickle file."""
```

**Storage Layout:**
```
data/traces/          ← One JSON file per trace (human-readable)
data/artifacts/       ← Parquet datasets for ML training
```

**Serialization:**
- Traces stored as JSON for human readability
- Datetimes converted to ISO format strings
- Enums converted to their string values
- For ML training, `export_pkl()` converts to pickle for faster loading

---

## Attribution Module

The attribution module (`blackbox/attribution/`) implements ML models for fault localization and confidence scoring.

### Model (`model.py`)

The core local attribution model that assigns suspicion scores to each step.

#### LocalAttributionModel

```python
class LocalAttributionModel:
    def __init__(self):
        """Initialize model with embedder and optional sklearn classifier."""
        self.embedder = TraceEmbedder(max_features=128)
        self.is_fitted = False
        self.feature_weights: list[float] = []
        self.feature_means: list[float] = []
        self.feature_stds: list[float] = []
        
        # Uses GradientBoostingClassifier if sklearn available
        # Falls back to pure Python statistical anomaly classifier
        if HAS_SKLEARN:
            self.clf = GradientBoostingClassifier(
                n_estimators=150,
                max_depth=5,
                learning_rate=0.05
            )
        else:
            self.clf = None
```

#### Training Process

**fit() method:**
```python
def fit(self, traces: list[AgentTrace], labels: LabelStore) -> None:
    """
    Train the attribution model on labeled traces.
    
    Process:
    1. Fit text embedder on all traces
    2. Build feature matrix (dense features + embeddings)
    3. If sklearn available: train GradientBoostingClassifier
    4. Otherwise: train pure Python discriminative classifier
    """
```

**Pure Python Learning (when sklearn unavailable):**
1. Compute feature means and standard deviations (z-score normalization)
2. Compute discriminative weights using Cohen's d (effect size)
3. Weight = (mean_positive - mean_negative) / pooled_std
4. Higher weights indicate features that distinguish fault from non-fault steps

#### Prediction Process

**predict_trace() method:**
```python
def predict_trace(self, trace: AgentTrace) -> dict[int, float]:
    """
    Predict suspicion scores for each step in a trace.
    
    Returns:
        dict[int, float]: Mapping from step_index to suspicion_score (0.0 to 1.0)
    
    Process:
    1. Extract features for each step
    2. If sklearn model fitted: use predict_proba
    3. If pure Python fitted: compute weighted dot product
    4. Apply bonuses: +5.0 for errors, +1.0 for high latency
    5. Apply earliest anomaly boost: earlier steps get higher scores
    6. Normalize scores to [0.05, 1.0] range
    """
```

**Heuristic Fallback:**
If model not fitted, uses simple heuristic:
- Base score: 0.1
- +0.8 if step has error
- +0.2 if latency > 200ms
- +0.15 if step is a tool call
- +0.2 × (1 - relative_position) for earliest step bias

#### Persistence

```python
def save(self, path: Path | str) -> None:
    """Save model state (embedder, classifier, weights) to pickle."""

def load(self, path: Path | str) -> None:
    """Load model state from pickle file."""
```

### Confidence (`confidence.py`)

Computes confidence tiers for model predictions.

```python
def compute_confidence(scores: dict[int, float]) -> str:
    """
    Returns 'high', 'medium', or 'low' based on the score margin.
    
    Logic:
    - High: Top score > 2× second score
    - Medium: Top score > 1.3× second score
    - Low: Otherwise
    """
```

### Baselines

The `baselines/` directory contains alternative attribution methods for comparison:

- **FirstError**: Simple baseline that blames the first step with an error
- **CloudJudge**: LLM-based attribution using semantic critique
- **GBM**: Gradient Boosting Machine (same as main model but isolated)

---

## Analysis Module

The analysis module (`blackbox/analysis/`) coordinates local and cloud analysis.

### Local Analysis (`local.py`)

Fast local analysis using the ML model.

```python
@dataclass
class LocalAnalysisResult:
    scores: dict[int, float]      # Suspicion scores per step
    top_step: int                 # Step with highest suspicion
    confidence: str              # "high", "medium", or "low"
    latency_ms: float             # Analysis latency

def analyze_local(trace: AgentTrace, model: LocalAttributionModel) -> LocalAnalysisResult:
    """
    Execute local ML analysis on a trace.
    
    Process:
    1. Start timer
    2. Call model.predict_trace(trace)
    3. Find step with max score
    4. Compute confidence tier
    5. Stop timer and return result
    
    Target latency: <50ms
    """
```

### Cloud Analysis (`cloud.py`)

Deep cloud analysis using LLM judge.

```python
@dataclass
class CloudAnalysisResult:
    scores: dict[int, float]      # Suspicion scores per step
    top_step: int                 # Step with highest suspicion
    confidence: str              # Confidence tier
    reasoning: str                # Human-readable LLM reasoning
    latency_ms: float             # Analysis latency
    token_usage: dict[str, int]   # Token consumption

def analyze_cloud(
    trace: AgentTrace,
    judge: CloudJudge | None = None
) -> CloudAnalysisResult:
    """
    Execute cloud LLM analysis on a trace.
    
    Process:
    1. Initialize CloudJudge (uses OpenAI/Gemini or heuristic fallback)
    2. Call judge.predict_sync(trace)
    3. Extract scores, top_step, confidence, reasoning
    4. Return result with latency and token usage
    
    Typical latency: 2-5 seconds (depends on LLM API)
    """
```

### Consensus (`consensus.py`)

Merges local and cloud analysis results.

```python
@dataclass
class ConsensusResult:
    scores: dict[int, float]      # Final merged scores
    top_step: int                 # Final culprit step
    agreement: bool               # Whether local and cloud agreed
    final_confidence: str         # Final confidence tier
    local_result: LocalAnalysisResult
    cloud_result: CloudAnalysisResult | None

def merge_consensus(
    local: LocalAnalysisResult,
    cloud: CloudAnalysisResult | None
) -> ConsensusResult:
    """
    Merge local and cloud analysis results.
    
    Logic:
    - If cloud unavailable: use local results
    - If local and cloud agree on top_step: high confidence
    - If they disagree: cloud overrides with reasoning
    """
```

---

## Features Module

The features module (`blackbox/features/`) extracts numeric features and text embeddings from traces.

### Step Features (`step_features.py`)

Extracts dense numeric features from individual steps.

```python
def extract_features(step: AgentStep, total_steps: int) -> list[float]:
    """
    Returns a fixed-length feature vector for the step.
    
    Features extracted:
    1. rel_pos: step_index / (total_steps - 1) - relative position
    2. is_llm: 1.0 if step is LLM_CALL, else 0.0
    3. is_tool: 1.0 if step is TOOL_CALL, else 0.0
    4. in_len_log: log(1 + len(inputs))
    5. out_len_log: log(1 + len(output))
    6. out_entropy: Shannon entropy of output text (capped at 1000 chars)
    7. latency_log: log(1 + latency_ms)
    8. has_error: 1.0 if step has error, else 0.0
    9. tok_in_log: log(1 + input_tokens) if available
    10. tok_out_log: log(1 + output_tokens) if available
    11-16. tool_*: One-hot encoding for known tools
    """
```

**Feature Names:**
```python
["rel_pos", "is_llm", "is_tool",
 "in_len_log", "out_len_log", "out_entropy",
 "latency_log", "has_error", "tok_in_log", "tok_out_log",
 "tool_calculator", "tool_search", "tool_retrieve",
 "tool_execute_sql", "tool_get_schema", "tool_none"]
```

**Shannon Entropy Calculation:**
```python
def _shannon_entropy(text: str) -> float:
    """
    Compute Shannon entropy of text (measure of information content).
    
    Higher entropy = more diverse/random character distribution
    Lower entropy = more repetitive/predictable text
    """
```

### Embeddings (`embeddings.py`)

Creates semantic embeddings for textual portions of traces.

```python
class TraceEmbedder:
    def __init__(self, max_features: int = 128):
        """
        Initialize embedder.
        
        If sklearn available: uses TfidfVectorizer
        Otherwise: uses pure Python n-gram bag-of-words
        """
        self.max_features = max_features
        self.is_fitted = False
        self.vocab: dict[str, int] = {}
        
        if HAS_SKLEARN:
            self.vectorizer = TfidfVectorizer(
                max_features=max_features,
                stop_words="english"
            )
        else:
            self.vectorizer = None

    def _step_to_text(self, step) -> str:
        """
        Convert a step to text representation.
        
        Format: "{tool} {name} {inputs_json[:200]} {output_str[:200]}"
        """

    def fit(self, traces: list[AgentTrace]) -> None:
        """
        Build vocabulary from all traces.
        
        sklearn: Fit TfidfVectorizer on all step texts
        Pure Python: Build frequency vocabulary, keep top N words
        """

    def transform_trace(self, trace: AgentTrace) -> list[list[float]]:
        """
        Convert trace to embedding vectors.
        
        sklearn: Use vectorizer.transform()
        Pure Python: Count word occurrences, normalize vectors
        """
```

**Pure Python Fallback:**
- Builds word frequency dictionary
- Keeps N most frequent words as vocabulary
- Creates normalized count vectors (L2 normalization)

### Dataset (`dataset.py`)

Builds ML-ready feature matrices from traces.

```python
def build_dataset(
    traces: list[AgentTrace],
    labels: LabelStore,
    embedder: TraceEmbedder
) -> tuple[list[list[float]], list[int]]:
    """
    Build feature matrix and label vector for ML training.
    
    Process:
    1. For each trace, extract step features
    2. Get text embeddings from embedder
    3. Concatenate dense features + embeddings
    4. Create label: 1 if step is fault step, else 0
    5. Return (X, y) where X is feature matrix, y is labels
    
    Returns:
        X: list of feature vectors (one per step across all traces)
        y: list of labels (1 for fault step, 0 otherwise)
    """
```

---

## Agents Module

The agents module (`blackbox/agents/`) implements multi-domain agent execution for generating synthetic traces.

### Runner (`runner.py`)

Scripted agent execution loop with fault injection support.

```python
def run(task_type: str, task: Any, *, run_id: str,
        injector: FaultInjector | None = None) -> AgentTrace:
    """
    Dispatch to domain-specific runner based on task_type.
    
    Supported task types:
    - "math": Mathematical reasoning tasks
    - "qa": Question answering with retrieval
    - "text2sql": Text-to-SQL generation
    """
```

**run_math() - Mathematical Reasoning:**
```python
def run_math(
    task: math_tasks.MathTask,
    *,
    run_id: str,
    injector: FaultInjector | None = None,
) -> AgentTrace:
    """
    Execute a math task through predefined step plan.
    
    Process:
    1. Build execution plan from task
    2. For each step in plan:
       - Check if fault should be injected
       - If yes: corrupt the output
       - Record step with TraceContext
    3. Compare final result with expected answer
    4. Build and return AgentTrace
    """
```

**run_qa() - Question Answering:**
```python
def run_qa(
    task: qa_tasks.QATask,
    *,
    run_id: str,
    injector: FaultInjector | None = None,
) -> AgentTrace:
    """
    Execute a QA task with search and retrieval.
    
    Steps typically include:
    1. LLM call to generate search query
    2. Tool call to search documents
    3. Tool call to retrieve specific document
    4. LLM call to answer question
    """
```

**run_text2sql() - Text-to-SQL:**
```python
def run_text2sql(
    task: sql_tasks.Text2SQLTask,
    *,
    run_id: str,
    injector: FaultInjector | None = None,
) -> AgentTrace:
    """
    Execute a Text2SQL task.
    
    Steps typically include:
    1. LLM call to understand question
    2. Tool call to get database schema
    3. LLM call to generate SQL
    4. Tool call to execute SQL
    5. LLM call to interpret results
    """
```

**Key Design Decision:**
The "scripted" approach means LLM decisions are fixed. This is intentional for training data generation - we need exact ground truth for fault localization evaluation.

### Tasks

Each domain has its own task definition module:

- **tasks/math.py**: Mathematical reasoning tasks with step plans
- **tasks/qa.py**: Question answering tasks with document retrieval
- **tasks/text2sql.py**: Text-to-SQL tasks with database schema

### Tools

Tool implementations used by agents:

- **tools/calculator.py**: Mathematical expression evaluation
- **tools/database.py**: SQL execution and schema retrieval
- **tools/search.py**: Document search and retrieval

---

## Faults Module

The faults module (`blackbox/faults/`) implements fault injection for generating training data.

### Injector (`injector.py`)

Orchestrates fault injection during agent execution.

```python
class FaultInjector:
    def __init__(self, fault_type: str, fault_step: int, rng: random.Random):
        """
        Initialize injector.
        
        Args:
            fault_type: Type of fault to inject (e.g., "bad_args", "fake_output")
            fault_step: Step index where fault should be injected
            rng: Random number generator for reproducibility
        """
        self.fault_type = fault_type
        self.fault_step = fault_step
        self._rng = rng
        self._impl = _REGISTRY.get(fault_type)

    def should_inject(self, step_index: int) -> bool:
        """Check if fault should be injected at this step."""
        return step_index == self.fault_step

    def corrupt(self, step_index: int, true_output: Any,
                step_plan: dict[str, Any]) -> Any:
        """
        Corrupt the output at the fault step.
        
        Delegates to fault-specific implementation function.
        """
        return self._impl(true_output, step_plan, self._rng)
```

**Fault Injection Flow:**
```
Normal:   Step 0 → Step 1 → Step 2 → Step 3 → Step 4
Injected: Step 0 → Step 1 → Step 2* → Step 3 → Step 4
                                   ↑
                              faulty step (index=2)
```

### Fault Library

The `library/` directory contains fault-specific implementations:

- **bad_args.py**: Corrupts tool arguments (e.g., wrong expression in calculator)
- **fake_output.py**: Returns completely fabricated output
- **poisoned_context.py**: Injects incorrect context in retrieved documents
- **truncation.py**: Truncates outputs to simulate token limits

**Example - bad_args:**
```python
def inject(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    """
    Corrupt tool arguments.
    
    For calculator: change "2+2" to "2/0" (causes division by zero)
    For SQL: change column names or table names
    """
```

### Labels (`labels.py`)

Stores ground truth fault labels for training.

```python
class LabelStore:
    def __init__(self, path: Path):
        """Initialize label store with JSON file."""

    def set(self, run_id: str, fault_step: int, fault_type: str) -> None:
        """Store ground truth label for a run."""

    def get(self, run_id: str) -> tuple[int, str] | None:
        """Retrieve ground truth label for a run."""

    def save(self) -> None:
        """Persist labels to JSON file."""
```

---

## Replay Module

The replay module (`blackbox/replay/`) implements checkpointing and time-travel execution.

### Checkpoint (`checkpoint.py`)

State reconstruction and snapshotting.

```python
def create_checkpoint(trace: AgentTrace, step_index: int) -> Checkpoint:
    """
    Create a checkpoint at a specific step.
    
    Process:
    1. Reconstruct agent state from steps 0 to step_index
    2. Capture all intermediate variables
    3. Serialize state to dict
    4. Return Checkpoint object
    """

def restore_state(checkpoint: Checkpoint) -> dict[str, Any]:
    """
    Restore agent state from checkpoint.
    
    Returns the state dict that can be used to resume execution.
    """
```

### Resume (`resume.py`)

Forward execution from checkpoint.

```python
def resume_from_checkpoint(
    checkpoint: Checkpoint,
    task: Any,
    patches: dict[int, Any] | None = None
) -> AgentTrace:
    """
    Resume execution from a checkpoint.
    
    Args:
        checkpoint: Checkpoint to resume from
        task: Task definition
        patches: Optional dict of step_index -> patched_output
    
    Process:
    1. Restore state from checkpoint
    2. Execute steps from checkpoint.step_index + 1 onwards
    3. Apply patches if specified
    4. Record new steps with TraceContext
    5. Return new AgentTrace (child trace)
    
    Benefits:
    - Skips re-execution of steps 0 to k
    - Saves computation time and tokens
    - Enables counterfactual testing
    """
```

### Cache (`cache.py`)

Deterministic tool result cache.

```python
class ToolCache:
    def __init__(self):
        """Initialize cache for tool results."""
        self._cache: dict[str, Any] = {}

    def get(self, tool_name: str, args: tuple) -> Any | None:
        """
        Get cached result for a tool call.
        
        Args:
            tool_name: Name of the tool
            args: Tuple of arguments (hashable)
        
        Returns cached result if available, else None.
        """

    def set(self, tool_name: str, args: tuple, result: Any) -> None:
        """Cache a tool result."""

    def clear(self) -> None:
        """Clear all cached results."""
```

---

## Debug Module

The debug module (`blackbox/debug/`) provides diagnosis and remediation suggestions.

### Diagnose (`diagnose.py`)

Creates human-readable diagnosis from attribution results.

```python
@dataclass
class Diagnosis:
    likely_source: int          # Most likely culprit step
    confidence: str            # Confidence tier
    rationale: str             # Human-readable explanation
    exception_type: str | None  # Exception type if applicable
    suggestions: list[str]     # Actionable suggestions

def create_diagnosis(
    trace: AgentTrace,
    consensus: ConsensusResult
) -> Diagnosis:
    """
    Create a diagnosis from consensus results.
    
    Process:
    1. Extract top culprit step from consensus
    2. Generate human-readable rationale
    3. Identify exception type if present
    4. Generate actionable suggestions
    5. Return Diagnosis object
    """
```

### Suggestions (`suggestions.py`)

Generates actionable remediation suggestions.

```python
def generate_suggestions(
    trace: AgentTrace,
    culprit_step: int
) -> list[str]:
    """
    Generate actionable suggestions for fixing the fault.
    
    Suggestion types:
    - "Override calculation": For math errors
    - "Repair tool arguments": For bad_args faults
    - "Filter poisoned context": For poisoned_context faults
    - "Retry with different parameters": For truncation faults
    - "Add error handling": For tool errors
    """
```

### Suspicion (`suspicion.py`)

Step suspicion ranking utilities.

```python
def rank_steps_by_suspicion(
    scores: dict[int, float]
) -> list[tuple[int, float]]:
    """
    Rank steps by suspicion score (descending).
    
    Returns list of (step_index, score) tuples.
    """
```

### Exceptions (`exceptions.py`)

Exception categorization.

```python
def categorize_exception(error: AgentError) -> str:
    """
    Categorize exception into known types.
    
    Categories:
    - "ZeroDivisionError": Division by zero
    - "SyntaxError": Invalid syntax
    - "DatabaseError": SQL execution errors
    - "ToolError": Generic tool failures
    - "ValidationError": Input validation failures
    - "SilentFailure": No exception but wrong output
    """
```

---

## Explain Module

The explain module (`blackbox/explain/`) provides explainability features.

### Saliency (`saliency.py`)

Computes feature importance for individual steps.

```python
@dataclass
class StepSaliency:
    step_index: int
    top_contributing_features: list[tuple[str, float]]
    summary: str

def compute_step_saliency(
    trace: AgentTrace,
    step_index: int
) -> StepSaliency:
    """
    Compute which features contributed most to the step's suspicion score.
    
    Process:
    1. Extract step features
    2. Get feature weights from model
    3. Compute contribution = feature_value × feature_weight
    4. Rank features by contribution
    5. Return top contributing features with summary
    """
```

### Rationale (`rationale.py`)

Builds human-readable explanations.

```python
def build_rationale(
    trace: AgentTrace,
    culprit_step: int,
    scores: dict[int, float]
) -> str:
    """
    Build a human-readable explanation of why this step was identified.
    
    Includes:
    - Step description
    - Suspicion score
    - Key contributing factors
    - Comparison to other steps
    """
```

### Contrast (`contrast.py`)

Contrastive explanation comparing culprit to normal steps.

```python
def contrast_explanation(
    trace: AgentTrace,
    culprit_step: int,
    reference_steps: list[int]
) -> str:
    """
    Generate contrastive explanation comparing culprit to reference steps.
    
    Highlights differences in:
    - Latency
    - Error states
    - Tool usage
    - Token consumption
    """
```

---

## Compare Module

The compare module (`blackbox/compare/`) implements trace diff and divergence detection.

### Align (`align.py`)

Step sequence alignment algorithm.

```python
def align_sequences(
    steps_a: list[AgentStep],
    steps_b: list[AgentStep]
) -> list[tuple[int | None, int | None]]:
    """
    Align two step sequences using dynamic programming.
    
    Returns list of (index_a, index_b) tuples where:
    - (i, j): Step i from A aligns with step j from B
    - (i, None): Step i only in A (deletion)
    - (None, j): Step j only in B (insertion)
    
    Similar to sequence alignment in bioinformatics.
    """
```

### Divergence (`divergence.py`)

Earliest divergence point detection.

```python
@dataclass
class DivergencePoint:
    step_index_a: int
    step_index_b: int
    divergence_type: str  # "output", "error", "tool_call", etc.
    description: str

def find_earliest_divergence(
    trace_a: AgentTrace,
    trace_b: AgentTrace
) -> DivergencePoint:
    """
    Find the earliest point where two traces diverge.
    
    Process:
    1. Align step sequences
    2. Compare aligned steps
    3. Find first step where outputs differ
    4. Return DivergencePoint with details
    
    Used for comparing failed runs vs repaired branches.
    """
```

---

## Evaluate Module

The evaluate module (`blackbox/evaluate/`) provides benchmark evaluation metrics.

### Localization (`localization.py`)

Top-K accuracy metrics.

```python
def top_k_accuracy(
    predictions: list[int],
    ground_truth: list[int],
    k: int = 1
) -> float:
    """
    Compute Top-K accuracy.
    
    Returns percentage of predictions where ground truth is in top K.
    """

def mean_reciprocal_rank(
    predictions: list[list[int]],
    ground_truth: list[int]
) -> float:
    """
    Compute Mean Reciprocal Rank (MRR).
    
    MRR = average of (1 / rank_of_ground_truth)
    Higher is better (max 1.0).
    """
```

### Confidence (`confidence.py`)

Confidence calibration metrics.

```python
def confidence_calibration(
    predictions: list[tuple[int, str]],
    ground_truth: list[int]
) -> dict[str, float]:
    """
    Compute confidence calibration metrics.
    
    Returns:
    - high_conf_accuracy: Accuracy when confidence is "high"
    - medium_conf_accuracy: Accuracy when confidence is "medium"
    - low_conf_accuracy: Accuracy when confidence is "low"
    """
```

### Generalization (`generalization.py`)

Cross-domain and cross-fault metrics.

```python
def cross_domain_accuracy(
    predictions: dict[str, list[int]],
    ground_truth: dict[str, list[int]]
) -> dict[str, float]:
    """
    Compute accuracy per domain (Math, QA, Text2SQL).
    
    Returns dict mapping domain to accuracy.
    """

def cross_fault_accuracy(
    predictions: dict[str, list[int]],
    ground_truth: dict[str, list[int]]
) -> dict[str, float]:
    """
    Compute accuracy per fault type.
    
    Returns dict mapping fault_type to accuracy.
    """
```

### Latency (`latency.py`)

SLA latency benchmarks.

```python
def latency_benchmark(
    latencies: list[float],
    target_ms: float = 50.0
) -> dict[str, float]:
    """
    Compute latency statistics.
    
    Returns:
    - mean_latency: Average latency
    - p50_latency: 50th percentile
    - p95_latency: 95th percentile
    - p99_latency: 99th percentile
    - sla_compliance: Percentage under target_ms
    """
```

### Replay Savings (`replay_savings.py`)

Computational and token savings from checkpointed replay.

```python
def compute_replay_savings(
    original_trace: AgentTrace,
    replayed_trace: AgentTrace,
    checkpoint_step: int
) -> dict[str, float]:
    """
    Compute savings achieved by checkpointed replay.
    
    Returns:
    - steps_saved: Number of steps skipped
    - steps_saved_pct: Percentage of steps skipped
    - time_saved_ms: Estimated time saved
    - tokens_saved: Number of tokens saved
    - tokens_saved_pct: Percentage of tokens saved
    """
```

### Counterfactual (`counterfactual.py`)

Repair success rate metrics.

```python
def counterfactual_success_rate(
    original_traces: list[AgentTrace],
    repaired_traces: list[AgentTrace]
) -> float:
    """
    Compute percentage of failed runs that succeeded after repair.
    
    Process:
    1. Identify originally failed traces
    2. Check if corresponding repaired traces succeeded
    3. Return success rate
    """
```

---

## Summary

The blackbox module provides a complete fault localization and debugging pipeline:

1. **Capture**: Record agent executions with TraceContext
2. **Features**: Extract numeric features and text embeddings
3. **Attribution**: ML model assigns suspicion scores
4. **Analysis**: Local (<50ms) and cloud (LLM) verification
5. **Debug**: Human-readable diagnosis and suggestions
6. **Replay**: Checkpointed time-travel execution
7. **Compare**: Trace diff and divergence detection
8. **Evaluate**: Comprehensive benchmark metrics

All modules are designed to work independently or together, providing flexibility for different use cases while maintaining a cohesive debugging workflow.
