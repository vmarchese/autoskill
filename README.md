# Autoskill

An automatic Skill optimizer inspired by [Karpathy's autoresearch loop](https://github.com/karpathy/autoresearch). Instead of optimizing LLM training, Autoskill iteratively optimizes an [Agent Skill](https://agentskills.io/home) by using Claude Code to propose improvements, evaluating them with Google ADK, and using git to keep improvements or revert regressions.

## How It Works

```
┌─────────────────────────────────────────────────┐
│                 Optimizer Loop                  │
│                                                 │
│  1. Claude Code reads SKILL.md + eval results   │
│  2. Claude Code proposes & implements changes   │
│  3. Skill runner evaluates against evals        │
│  4. If improved → git commit                   │
│     If not     → git revert                    │
│  5. Repeat until convergence or max iterations  │
└─────────────────────────────────────────────────┘
```

Each iteration:
- Claude Code (non-interactive) examines the current skill, past eval results, and a memory file of previous attempts
- Changes are made to `SKILL.md` only
- The skill runner executes each eval case using Google ADK with a configurable LLM
- An LLM judge grades each assertion as PASS/FAIL
- The overall `pass_rate` determines whether changes are kept (committed) or reverted

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- API key for at least one LLM provider (OpenAI, Anthropic, Google, or Azure OpenAI)

## Setup

```bash
# Install dependencies
uv sync

# Set your API key(s) depending on your provider
export OPENAI_API_KEY="your-key"
# and/or
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"

# For Azure OpenAI
export AZURE_API_KEY="your-azure-key"
export AZURE_API_BASE="https://your-resource.openai.azure.com/"
export AZURE_API_VERSION="2024-06-01"
```

## Usage

```bash
# Run with defaults (event-extractor skill, openai/gpt-4o-mini, 20 iterations)
bash optimizer_loop.sh

# Customize via environment variables
SKILL_DIR=skill/my-skill MODEL=anthropic/claude-3-haiku-20240307 MAX_ITERATIONS=10 PATIENCE=2 bash optimizer_loop.sh

# Use Azure OpenAI (model string is azure/<your-deployment-name>)
MODEL=azure/gpt-4o-mini bash optimizer_loop.sh
```

### Run the skill runner standalone

```bash
source .venv/bin/activate
python skill_runner.py --skill-dir skill/event-extractor --model openai/gpt-4o-mini --output run.txt
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILL_DIR` | `skill/event-extractor` | Path to the skill directory |
| `MODEL` | `openai/gpt-4o-mini` | LiteLLM model string for both the skill agent and judge (see [Supported Models](#supported-models)) |
| `MAX_ITERATIONS` | `20` | Maximum optimization iterations |
| `PATIENCE` | `3` | Stop after this many iterations without improvement |

## Supported Models

The `MODEL` variable accepts any [LiteLLM model string](https://docs.litellm.ai/docs/providers). Common examples:

| Provider | Model String | Required Env Vars |
|----------|-------------|-------------------|
| OpenAI | `openai/gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-3-haiku-20240307` | `ANTHROPIC_API_KEY` |
| Google Gemini | `gemini/gemini-pro` | `GOOGLE_API_KEY` |
| Azure OpenAI | `azure/<deployment-name>` | `AZURE_API_KEY`, `AZURE_API_BASE`, `AZURE_API_VERSION` |
| Ollama (local) | `ollama/<model-name>` | None (Ollama must be running on `localhost:11434`) |

## Project Structure

```
autoskill/
├── skill/
│   └── event-extractor/        # Sample skill: structured event data extraction
│       ├── SKILL.md            # Skill instructions (what gets optimized)
│       └── evals/
│           └── evals.json      # Evaluation dataset with assertions
├── skill_runner.py             # Eval runner using Google ADK (do not modify)
├── optimizer_loop.sh           # Main optimization loop
├── instructions.md             # Claude Code instructions for proposing changes
├── runs/                       # Runtime artifacts (gitignored)
│   └── memory-<runid>.txt      # Per-run change log and results
└── run.txt                     # Latest eval metrics (gitignored)
```

## Creating Your Own Skill

1. Create a new directory under `skill/`:
   ```
   skill/my-skill/
   ├── SKILL.md
   └── evals/
       └── evals.json
   ```

2. Write `SKILL.md` with YAML frontmatter and instructions:
   ```markdown
   ---
   name: my-skill
   description: What the skill does and when to use it.
   ---
   # My Skill
   Instructions for the agent...
   ```

3. Create `evals/evals.json` with test cases:
   ```json
   {
     "skill_name": "my-skill",
     "evals": [
       {
         "id": 1,
         "prompt": "User message to test...",
         "expected_output": "Description of expected output.",
         "assertions": [
           "The output should contain X",
           "The output should not contain Y"
         ]
       }
     ]
   }
   ```

4. Run the optimizer:
   ```bash
   SKILL_DIR=skill/my-skill bash optimizer_loop.sh
   ```
