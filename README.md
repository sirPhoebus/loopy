# Ralph Loop

Ralph Loop is an autonomous coding agent implementation that follows a strict feedback loop to achieve goals. It uses a system prompt loaded from a markdown file to define its behavior and goals.

## Project Structure

- `main.py`: The core engine that runs the Ralph Loop.
- `system_prompt.md`: The detailed identity and workflow instructions for the agent.
- `project/`: The directory where Ralph performs its work.
  - `idea.txt`: The initial high-level idea provided by the user.
  - `prd.md`: The Product Requirements Document managed by Ralph.
  - `progress.txt`: An execution log of Ralph's actions and reasoning.

## Getting Started

1. Create a virtual environment: `python -m venv .venv`
2. Activate the environment and install dependencies (e.g., `openai`).
3. Run the loop: `python main.py`
4. Enter your idea when prompted.

## How it Works

Ralph reads its context from the `project/` directory, interacts with a local LLM server (defaulting to `http://localhost:1234/v1`), and writes file changes using a specific XML format. It continues until all tasks in `prd.md` are marked as complete.
