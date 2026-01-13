# Loopy

Loopy is an autonomous coding agent implementation that follows a strict feedback loop to achieve goals. It uses a system prompt loaded from a markdown file to define its behavior and goals. By default, it is configured to use a local model (e.g., LM Studio) via an OpenAI-compatible API.

## Project Structure

- `main.py`: The core engine that runs the Loopy loop.
- `system_prompt.md`: The detailed identity and workflow instructions for the agent.
- `config.json`: Configuration file for model settings.
- `project/`: The directory where Loopy performs its work.
  - `idea.txt`: The initial high-level idea provided by the user.
  - `prd.md`: The Product Requirements Document managed by Loopy.
  - `progress.txt`: An execution log of Loopy's actions (summaries only, no code).
  - `test_*.py`: Test files created by Loopy to verify features.

## Getting Started

1. Create a virtual environment: `python -m venv .venv`
2. Activate it: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux/Mac)
3. Install dependencies: `pip install openai`
4. Customize `config.json` with your model settings.
5. Run the loop: `python main.py`
6. Enter your idea when prompted.

## Configuration

Loopy uses a `config.json` file for all its settings:

| Setting | Description | Default |
|---------|-------------|---------|
| `base_url` | URL of your LLM server | `http://localhost:1234/v1` |
| `api_key` | API key if required | `sk-no-key-required` |
| `model` | Model identifier | `local-model` |
| `max_chars` | Context window limit for progress log | `60000` |
| `max_iterations` | Safety limit for loop iterations | `100` |
| `temperature` | Model temperature | `0.7` |
| `max_tokens` | Max tokens per response | `96000` |

## Features

### Thinking Model Support
Loopy automatically strips `<think>...</think>` tags from models like GLM-4 that include reasoning traces, so only the actionable output is processed.

### Code Artifact Extraction
The model outputs code in `<write_file path="filename">` blocks, which Loopy extracts and writes to the project folder. Debug logging shows extraction progress:
```
[DEBUG] Found 2 write_file block(s): ['main.py', 'prd.md']
[OK] Wrote: main.py
```

### Mandatory Testing
Loopy **must create test files** (`test_*.py`) before declaring completion. The `<<<ALL_TASKS_COMPLETE>>>` signal is only valid when:
- All PRD checkboxes are `[x]`
- Test files exist for each feature
- All tests would pass

### Context Windowing
The `progress.txt` file grows over time. To prevent context overflow, Loopy only sends the last `max_chars` of the progress log to the model, preserving recent history while staying within token limits.

## How it Works

1. Loopy reads `idea.txt`, `prd.md`, and `progress.txt` from the `project/` folder
2. Sends the context to the LLM with the system prompt
3. Extracts `<summary>` for progress logging (no code bloat)
4. Extracts `<write_file>` blocks and writes actual code files
5. Repeats until `<<<ALL_TASKS_COMPLETE>>>` or max iterations reached

## Debugging

When code files aren't being created, check the console output:
- `[DEBUG] Found N write_file block(s)` - Blocks were extracted successfully
- `[DEBUG] WARNING: Response mentions files but no valid <write_file> blocks` - Model isn't using the correct format
- `[INFO] No files written this iteration` - Normal for planning/analysis iterations
