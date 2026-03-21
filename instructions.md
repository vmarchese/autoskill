# Skill Optimization Instructions

You are optimizing an Agent Skill to maximize its eval pass rate.

## Context

- The skill directory is specified by the SKILL_DIR environment variable
- The only file you may modify is the SKILL.md file inside that directory
- Do NOT modify any eval files, skill_runner.py, or any other files outside the skill directory

## Your Task

1. Read the SKILL.md file in the skill directory to understand the current instructions
2. Read `evals/evals.json` inside the skill directory to understand what is being tested
3. Read `run.txt` (if it exists) to see the latest eval results including which assertions failed
4. Read the memory file (path given in MEMORY_FILE env variable) for history of past changes and results
5. Based on failed assertions and past attempts, propose targeted improvements to SKILL.md
6. Implement the changes by editing SKILL.md

## Improvement Guidelines

- Focus on assertions that FAILED — these are your optimization targets
- Look at per_eval results in run.txt to understand which specific assertions failed and why
- Generalize fixes: do not hardcode answers to specific eval prompts
- Keep instructions concise — shorter, clearer instructions often outperform verbose ones
- Add concrete examples of desired output format if formatting assertions are failing
- Explain WHY the agent should do something, not just WHAT
- Do not add instructions that contradict each other
- Review the memory file to avoid repeating changes that were already tried and reverted
- If a previous change was reverted, try a different approach to address the same problem
- Consider adding explicit constraints (word counts, bullet counts) if quantitative assertions fail

## Output

After making changes, print a one-line summary to stdout in this exact format:
CHANGES: <description of what was changed and why>
