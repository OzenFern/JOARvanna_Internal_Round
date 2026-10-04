# Configuration Guide

This document provides detailed documentation for the YAML configuration files in the `configs/` directory.

## Table of Contents

- [Overview](#overview)
- [Experiments Configuration](#experiments-configuration)
- [Faults Configuration](#faults-configuration)
- [Tasks Configuration](#tasks-configuration)
- [Models Configuration](#models-configuration)

---

## Overview

The `configs/` directory contains YAML configuration files for various aspects of the system:

```
configs/
├── experiments/    # Experiment and training configurations
├── faults/         # Fault injection parameters
├── models/         # Model and LLM configurations
└── tasks/          # Task domain configurations
```

These configurations allow you to customize:
- Training parameters and evaluation settings
- Fault injection behavior and probabilities
- Task domain definitions and tool requirements
- Model hyperparameters and LLM API settings

---

## Experiments Configuration

**Directory**: `configs/experiments/`

Contains experiment configurations for training and evaluation runs.

### default.yaml

Default training and evaluation configuration.

```yaml
name: "Default Training & Eval"
train_n: 1000
eval_n: 200
held_out_faults: []
```

**Parameters:**
- **name**: Human-readable experiment name
- **train_n**: Number of training traces to generate
- **eval_n**: Number of evaluation traces to generate
- **held_out_faults**: List of fault types to hold out during training (for generalization testing)

**Usage:**
```python
import yaml

with open("configs/experiments/default.yaml") as f:
    config = yaml.safe_load(f)

train_traces = generate_traces(n=config["train_n"])
eval_traces = generate_traces(n=config["eval_n"])
```

### generalization.yaml

Configuration for cross-domain generalization experiments.

```yaml
name: "Generalization Test"
train_n: 1000
eval_n: 200
held_out_faults: ["truncation"]
```

**Purpose:**
Tests model generalization by holding out specific fault types during training. This evaluates whether the model can detect unseen fault categories.

**Usage:**
```python
# Train without truncation faults
train_traces = generate_traces(
    n=config["train_n"],
    fault_types=[f for f in ALL_FAULTS if f not in config["held_out_faults"]]
)

# Evaluate with all fault types including truncation
eval_traces = generate_traces(n=config["eval_n"])
```

---

## Faults Configuration

**Directory**: `configs/faults/`

Contains fault injection parameters for each fault type.

### bad_args.yaml

Configuration for bad argument faults.

```yaml
fault_type: "bad_args"
description: "Corrupt tool arguments or LLM intermediate outputs."
probability: 1.0
```

**Behavior:**
- Corrupts tool arguments (e.g., changing "2+2" to "2/0" in calculator)
- Corrupts LLM intermediate outputs
- Probability determines how often this fault is selected when multiple faults are possible

**Examples:**
- Math: Change calculator expression from "2+2" to "2/0" (division by zero)
- SQL: Change column name from "price" to "pric" (column not found)
- QA: Change search query to return irrelevant documents

### fake_output.yaml

Configuration for fake output faults.

```yaml
fault_type: "fake_output"
description: "Return completely fabricated output."
probability: 1.0
```

**Behavior:**
- Returns completely fabricated or random output
- Simulates hallucination or tool malfunction
- Useful for testing detection of semantic errors

**Examples:**
- Math: Return random number instead of calculation result
- SQL: Return empty list instead of query results
- QA: Return fabricated answer instead of retrieved facts

### poisoned_context.yaml

Configuration for poisoned context faults.

```yaml
fault_type: "poisoned_context"
description: "Inject incorrect context in retrieved documents."
probability: 1.0
```

**Behavior:**
- Injects incorrect information into retrieved documents
- Simulates retrieval of outdated or incorrect data
- Particularly relevant for QA tasks with document retrieval

**Examples:**
- QA: Retrieve document with wrong answer
- QA: Inject contradictory information into context
- SQL: Return schema with wrong column types

### truncation.yaml

Configuration for truncation faults.

```yaml
fault_type: "truncation"
description: "Truncate outputs to simulate token limits."
probability: 1.0
```

**Behavior:**
- Truncates outputs to simulate token limits
- Cuts off responses mid-sentence or mid-calculation
- Tests detection of incomplete results

**Examples:**
- LLM: Truncate response after 50 tokens
- Calculator: Return partial result
- SQL: Return only first N rows

**Usage in Code:**
```python
from blackbox.faults.injector import FaultInjector

# Load fault configuration
with open("configs/faults/bad_args.yaml") as f:
    fault_config = yaml.safe_load(f)

# Create injector
injector = FaultInjector(
    fault_type=fault_config["fault_type"],
    fault_step=2,
    rng=random.Random(42)
)
```

---

## Tasks Configuration

**Directory**: `configs/tasks/`

Contains task domain definitions and tool requirements.

### math.yaml

Configuration for mathematical reasoning tasks.

```yaml
name: "Math Problem Solving"
task_type: "math"
tools:
  - "calculator"
max_steps: 15
```

**Parameters:**
- **name**: Human-readable task name
- **task_type**: Internal task identifier ("math", "qa", "text2sql")
- **tools**: List of tools available for this task type
- **max_steps**: Maximum number of steps allowed for execution

**Tool Details:**
- **calculator**: Evaluates mathematical expressions
- Supports basic arithmetic: +, -, *, /
- Handles parentheses for order of operations

**Example Task:**
```
Task: "Calculate (5 + 3) * 2"
Steps:
  1. LLM: Parse expression
  2. Calculator: Evaluate (5 + 3) = 8
  3. Calculator: Evaluate 8 * 2 = 16
  4. LLM: Format answer
```

### qa_tools.yaml

Configuration for question answering tasks with tools.

```yaml
name: "Question Answering with Retrieval"
task_type: "qa"
tools:
  - "search"
  - "retrieve"
max_steps: 20
```

**Parameters:**
- **tools**: Search and retrieve tools for document access
- **max_steps**: Higher limit due to retrieval steps

**Tool Details:**
- **search**: Searches document corpus by query
- **retrieve**: Retrieves specific document by ID

**Example Task:**
```
Task: "What is the capital of France?"
Steps:
  1. LLM: Generate search query
  2. Search: Search for "capital France"
  3. Retrieve: Retrieve top document
  4. LLM: Extract answer from document
```

### text2sql.yaml

Configuration for text-to-SQL generation tasks.

```yaml
name: "Text-to-SQL Generation"
task_type: "text2sql"
tools:
  - "get_schema"
  - "execute_sql"
max_steps: 25
```

**Parameters:**
- **tools**: Database schema retrieval and SQL execution
- **max_steps**: Highest limit due to schema inspection

**Tool Details:**
- **get_schema**: Retrieves database schema (tables, columns, types)
- **execute_sql**: Executes SQL query and returns results

**Example Task:**
```
Task: "Find all users with age > 25"
Steps:
  1. LLM: Understand question
  2. Get Schema: Retrieve users table schema
  3. LLM: Generate SQL: SELECT * FROM users WHERE age > 25
  4. Execute SQL: Run query
  5. LLM: Format results
```

**Usage in Code:**
```python
import yaml

# Load task configuration
with open("configs/tasks/math.yaml") as f:
    task_config = yaml.safe_load(f)

# Configure agent
agent = Agent(
    task_type=task_config["task_type"],
    available_tools=task_config["tools"],
    max_steps=task_config["max_steps"]
)
```

---

## Models Configuration

**Directory**: `configs/models/`

Contains model and LLM API configurations.

### cloud.yaml

Configuration for cloud LLM verification.

```yaml
provider: "openai"
model: "gpt-4"
api_key_env: "OPENAI_API_KEY"
temperature: 0.0
max_tokens: 1000
timeout: 30
```

**Parameters:**
- **provider**: LLM provider ("openai", "gemini", "mock")
- **model**: Model identifier
- **api_key_env**: Environment variable name for API key
- **temperature**: Sampling temperature (0.0 for deterministic)
- **max_tokens**: Maximum tokens in response
- **timeout**: Request timeout in seconds

**Providers:**
- **openai**: Uses OpenAI API (requires OPENAI_API_KEY)
- **gemini**: Uses Google Gemini API (requires GEMINI_API_KEY)
- **mock**: Uses heuristic fallback (no API key required)

**Usage:**
```python
import yaml
import os

with open("configs/models/cloud.yaml") as f:
    config = yaml.safe_load(f)

api_key = os.getenv(config["api_key_env"])
if api_key:
    judge = CloudJudge(
        provider=config["provider"],
        model=config["model"],
        api_key=api_key,
        temperature=config["temperature"]
    )
else:
    judge = CloudJudge(provider="mock")  # Fallback
```

### local.yaml

Configuration for local ML model.

```yaml
model_type: "gradient_boosting"
n_estimators: 150
max_depth: 5
learning_rate: 0.05
max_features: 128
```

**Parameters:**
- **model_type**: Type of model ("gradient_boosting", "pure_python")
- **n_estimators**: Number of trees in gradient boosting
- **max_depth**: Maximum depth of trees
- **learning_rate**: Learning rate for gradient boosting
- **max_features**: Maximum number of text embedding features

**Model Types:**
- **gradient_boosting**: Uses sklearn GradientBoostingClassifier (requires scikit-learn)
- **pure_python**: Uses statistical anomaly classifier (no dependencies)

**Usage:**
```python
import yaml

with open("configs/models/local.yaml") as f:
    config = yaml.safe_load(f)

model = LocalAttributionModel(
    n_estimators=config["n_estimators"],
    max_depth=config["max_depth"],
    learning_rate=config["learning_rate"],
    max_features=config["max_features"]
)
```

---

## Configuration Loading Pattern

All configurations follow a consistent loading pattern:

```python
import yaml
from pathlib import Path

def load_config(config_path: Path) -> dict:
    """Load YAML configuration file."""
    with open(config_path) as f:
        return yaml.safe_load(f)

# Example usage
experiment_config = load_config(Path("configs/experiments/default.yaml"))
fault_config = load_config(Path("configs/faults/bad_args.yaml"))
task_config = load_config(Path("configs/tasks/math.yaml"))
model_config = load_config(Path("configs/models/local.yaml"))
```

---

## Custom Configuration

To create custom configurations:

### 1. Custom Experiment

Create `configs/experiments/custom.yaml`:
```yaml
name: "Custom Experiment"
train_n: 500
eval_n: 100
held_out_faults: ["fake_output", "truncation"]
```

### 2. Custom Fault

Create `configs/faults/custom_fault.yaml`:
```yaml
fault_type: "custom_fault"
description: "Custom fault description"
probability: 0.5
```

Then implement the fault in `blackbox/faults/library/custom_fault.py`:
```python
def inject(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    """Implement custom fault injection logic."""
    # Your custom logic here
    return modified_output
```

Register in `blackbox/faults/injector.py`:
```python
@register_fault("custom_fault")
def _custom_fault(true_output: Any, step_plan: dict, rng: random.Random) -> Any:
    from blackbox.faults.library.custom_fault import inject
    return inject(true_output, step_plan, rng)
```

### 3. Custom Task

Create `configs/tasks/custom.yaml`:
```yaml
name: "Custom Task Domain"
task_type: "custom"
tools:
  - "tool1"
  - "tool2"
max_steps: 30
```

Implement task logic in `blackbox/agents/tasks/custom.py`.

---

## Environment Variables

Some configurations rely on environment variables:

### OpenAI API Key

```bash
# Linux/macOS
export OPENAI_API_KEY="sk-..."

# Windows CMD
set OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:OPENAI_API_KEY="sk-..."
```

### Gemini API Key

```bash
# Linux/macOS
export GEMINI_API_KEY="..."

# Windows CMD
set GEMINI_API_KEY="..."

# Windows PowerShell
$env:GEMINI_API_KEY="..."
```

### Custom Model Path

```bash
# Override default model path
export BLACKBOX_MODEL_PATH="/custom/path/to/model.pkl"
```

---

## Summary

Configuration files provide a flexible way to customize the Black Box system:

- **Experiments**: Control training and evaluation parameters
- **Faults**: Define fault injection behavior
- **Tasks**: Specify task domains and tool requirements
- **Models**: Configure ML model and LLM API settings

All configurations use YAML for human readability and easy modification. They can be loaded programmatically and used to control system behavior without code changes.
