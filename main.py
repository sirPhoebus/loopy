import os
import time
import json
from openai import OpenAI

# Load Config
config_path = "config.json"
if not os.path.exists(config_path):
    # Default settings if config file is missing
    config = {
        "base_url": "http://localhost:1234/v1",
        "api_key": "sk-no-key-required",
        "model": "local-model",
        "project_dir": "project",
        "max_iterations": 100,
        "system_prompt_path": "system_prompt.md",
        "max_chars": 60000,
        "temperature": 0.7,
        "max_tokens": 128000
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    print(f"Created default {config_path}")
else:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

BASE_URL = config.get("base_url")
API_KEY = config.get("api_key")
MODEL = config.get("model")
PROJECT_DIR = config.get("project_dir")
MAX_ITERATIONS = config.get("max_iterations")
SYSTEM_PROMPT_PATH = config.get("system_prompt_path")
MAX_CHARS = config.get("max_chars")
TEMPERATURE = config.get("temperature")
MAX_TOKENS = config.get("max_tokens")

# Load SYSTEM_PROMPT from file
if os.path.exists(SYSTEM_PROMPT_PATH):
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
else:
    # Fallback or error if necessary, though requested to adapt for MD file
    print(f"Warning: {SYSTEM_PROMPT_PATH} not found.")
    SYSTEM_PROMPT = "You are a helpful coding assistant."

# Ensure project dir exists
os.makedirs(PROJECT_DIR, exist_ok=True)

# Paths
idea_path = os.path.join(PROJECT_DIR, "idea.txt")
prd_path = os.path.join(PROJECT_DIR, "prd.md")
progress_path = os.path.join(PROJECT_DIR, "progress.txt")

# Initialize idea.txt if missing
if not os.path.exists(idea_path):
    idea = input("Enter your IDEA (one sentence or paragraph): ").strip()
    with open(idea_path, "w", encoding="utf-8") as f:
        f.write(idea + "\n")
    print(f"Created {idea_path}")

# Initialize empty progress.txt if missing
if not os.path.exists(progress_path):
    with open(progress_path, "w", encoding="utf-8") as f:
        f.write("Loopy started\n\n")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def read_file(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "(file does not exist)"

def strip_thinking_tags(response):
    """Remove <think>...</think> blocks from thinking models like GLM-4."""
    import re
    # Remove think blocks (can be multiline)
    cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    # Also handle unclosed think tags (model started thinking but didn't close)
    cleaned = re.sub(r'<think>.*$', '', cleaned, flags=re.DOTALL)
    return cleaned.strip()

def get_truncated_progress(content, max_chars=None):
    """Keep the last part of the progress log to stay within context limits."""
    if max_chars is None:
        max_chars = MAX_CHARS
    if len(content) > max_chars:
        return "...(older logs truncated)...\n" + content[-max_chars:]
    return content

def extract_write_blocks(response):
    import re
    # Single robust pattern that handles quotes optionally
    pattern = r'<write_file\s+path=["\']?([^"\'<>\s]+)["\']?\s*>(.*?)</write_file>'
    
    raw_blocks = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
    
    # Clean paths and deduplicate by filename (keep first occurrence)
    seen_paths = set()
    blocks = []
    for path, content in raw_blocks:
        # Strip any remaining quotes from path
        clean_path = path.strip().strip('"').strip("'")
        if clean_path not in seen_paths:
            seen_paths.add(clean_path)
            blocks.append((clean_path, content))
    
    # Debug logging
    if blocks:
        print(f"[DEBUG] Found {len(blocks)} write_file block(s): {[b[0] for b in blocks]}")
    else:
        # Check if model mentioned file writing but didn't use correct format
        if 'write_file' in response.lower() or ('create' in response.lower() and '.py' in response):
            print("[DEBUG] WARNING: Response mentions files but no valid <write_file> blocks extracted!")
            print("[DEBUG] Check if model is using correct XML format.")
        else:
            print("[DEBUG] No write_file blocks in this response.")
    
    return blocks

def extract_summary(response):
    import re
    match = re.search(r"<summary>(.*?)</summary>", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return "No summary provided in this iteration."

iteration = 1
while iteration <= MAX_ITERATIONS:
    print(f"\n=== Loopy Iteration {iteration} ===")
    
    # Build context: idea + prd + progress + any existing code files (simple list)
    idea = read_file(idea_path)
    prd = read_file(prd_path)
    # Window the progress to prevent context overflow (fixed 400 - context length reached)
    full_progress = read_file(progress_path)
    progress = get_truncated_progress(full_progress)
    
    context = f"""
IDEA:
{idea}

CURRENT PRD:
{prd}

CURRENT PROGRESS LOG:
{progress}

Other files in project (you can request READ if needed):
{', '.join(f for f in os.listdir(PROJECT_DIR) if f not in ['idea.txt', 'prd.md', 'progress.txt'])}
"""

    # Create a fresh session for each iteration. 
    # We only send the system prompt and the current project state (IDEA + PRD + PROGRESS).
    # This ensures the model doesn't get confused by previous iteration turns, 
    # as the entire history is already summarized in progress.txt.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.replace("{current_date}", time.strftime("%Y-%m-%d"))},
        {"role": "user", "content": context + "\nContinue the Loopy loop."}
    ]
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    ).choices[0].message.content
    
    print("\nModel raw response:\n", response[:500], "..." if len(response) > 500 else "")
    
    # Strip <think> tags from thinking models (e.g., GLM-4)
    response = strip_thinking_tags(response)
    print("\n[DEBUG] Response after stripping <think> tags:", len(response), "chars")
    
    # Extract iteration summary (ensure no code leaks into progress.txt)
    summary = extract_summary(response)
    
    # Always append model reasoning to progress.txt for persistence
    with open(progress_path, "a", encoding="utf-8") as f:
        f.write(f"\n--- Iteration {iteration} ---\n{summary}\n")
    
    # Apply any <write_file> blocks
    writes = extract_write_blocks(response)
    if writes:
        for rel_path, content in writes:
            rel_path = rel_path.strip()
            # Handle absolute vs relative paths
            if os.path.isabs(rel_path):
                full_path = rel_path
            else:
                full_path = os.path.join(PROJECT_DIR, rel_path)
            
            # Ensure parent directory exists
            parent_dir = os.path.dirname(full_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content.strip() + "\n")
            print(f"[OK] Wrote: {rel_path}")
    else:
        print("[INFO] No files written this iteration.")
    
    # Check for completion
    if "<<<ALL_TASKS_COMPLETE>>>" in response:
        print("\nLoopy reports all tasks complete! Stopping.")
        break
    
    iteration += 1
    time.sleep(1)  # be gentle on your local server

print("\nDone! Check your project/ folder.")