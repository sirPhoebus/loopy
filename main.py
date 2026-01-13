import os
import time
from openai import OpenAI

# Config
BASE_URL = "http://localhost:1234/v1"
API_KEY = "sk-no-key-required"  # common for local servers
MODEL = "local-model"  # or whatever name your endpoint expects, e.g. "gpt-4o" or the actual model name
PROJECT_DIR = "project"
MAX_ITERATIONS = 100  # safety limit
SYSTEM_PROMPT_PATH = "system_prompt.md"

# Load SYSTEM_PROMPT from file
if os.path.exists(SYSTEM_PROMPT_PATH):
    with open(SYSTEM_PROMPT_PATH, "r") as f:
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
    with open(idea_path, "w") as f:
        f.write(idea + "\n")
    print(f"Created {idea_path}")

# Initialize empty progress.txt if missing
if not os.path.exists(progress_path):
    with open(progress_path, "w") as f:
        f.write("Ralph Loop started\n\n")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def read_file(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return "(file does not exist)"

def extract_write_blocks(response):
    import re
    blocks = re.findall(r"<write_file path=\"(.*?)\"\s*>(.*?)</write_file>", response, re.DOTALL)
    return blocks

iteration = 1
while iteration <= MAX_ITERATIONS:
    print(f"\n=== Ralph Iteration {iteration} ===")
    
    # Build context: idea + prd + progress + any existing code files (simple list)
    idea = read_file(idea_path)
    prd = read_file(prd_path)
    progress = read_file(progress_path)
    
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

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.replace("{current_date}", time.strftime("%Y-%m-%d"))},
        {"role": "user", "content": context + "\nContinue the Ralph Loop."}
    ]
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=4000,  # adjust as needed
    ).choices[0].message.content
    
    print("\nModel response:\n", response)
    
    # Always append model reasoning to progress.txt for persistence
    with open(progress_path, "a") as f:
        f.write(f"\n--- Iteration {iteration} ---\n{response}\n")
    
    # Apply any <write_file> blocks
    writes = extract_write_blocks(response)
    if writes:
        for rel_path, content in writes:
            full_path = os.path.join(PROJECT_DIR, rel_path.strip())
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content.strip() + "\n")
            print(f"Wrote {rel_path}")
    
    # Check for completion
    if "<<<ALL_TASKS_COMPLETE>>>" in response:
        print("\nRalph reports all tasks complete! Stopping.")
        break
    
    iteration += 1
    time.sleep(1)  # be gentle on your local server

print("\nDone! Check your project/ folder.")