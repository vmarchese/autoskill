#!/usr/bin/env python3
"""Skill runner: executes a skill against its evals and produces metrics.

Usage:
    python skill_runner.py --skill-dir skill/text-summarizer \
                           --model openai/gpt-4o-mini \
                           --output run.txt
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import yaml
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Default timeout in seconds for LiteLLM API calls
DEFAULT_TIMEOUT = 120


def parse_skill_md(skill_dir: Path) -> dict:
    """Parse SKILL.md frontmatter and body into a dict."""
    skill_path = skill_dir / "SKILL.md"
    text = skill_path.read_text()

    # Split YAML frontmatter from body
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {"name": skill_dir.name, "description": "", "instruction": text}

    frontmatter = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()

    return {
        "name": frontmatter.get("name", skill_dir.name),
        "description": frontmatter.get("description", ""),
        "instruction": body,
    }


def load_evals(skill_dir: Path) -> list[dict]:
    """Load evals/evals.json and return the evals list."""
    evals_path = skill_dir / "evals" / "evals.json"
    data = json.loads(evals_path.read_text())
    return data["evals"]


async def run_single_eval(
    eval_case: dict,
    skill_instruction: str,
    model: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Run one eval case through the ADK agent and return raw output."""
    agent = LlmAgent(
        model=LiteLlm(model=model, timeout=timeout),
        name="skill_agent",
        instruction=skill_instruction,
    )
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="autoskill",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="autoskill",
        user_id="eval-user",
    )
    content = types.Content(
        role="user",
        parts=[types.Part(text=eval_case["prompt"])],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id="eval-user",
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text

    return {"eval_id": eval_case["id"], "output": final_text}


async def grade_assertion(
    assertion: str,
    agent_output: str,
    original_prompt: str,
    model: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Use LLM-as-judge to grade a single assertion against the agent output."""
    judge_instruction = (
        "You are an eval grader. You will be given an agent's output and an assertion "
        "to check against that output. Determine if the assertion PASSES or FAILS.\n\n"
        "Respond with ONLY a JSON object in this exact format, no other text:\n"
        '{"passed": true, "evidence": "brief explanation"}\n'
        "or\n"
        '{"passed": false, "evidence": "brief explanation"}'
    )

    judge_agent = LlmAgent(
        model=LiteLlm(model=model, timeout=timeout),
        name="judge",
        instruction=judge_instruction,
    )
    session_service = InMemorySessionService()
    runner = Runner(
        agent=judge_agent,
        app_name="autoskill_judge",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="autoskill_judge",
        user_id="judge-user",
    )

    judge_prompt = (
        f"Original prompt given to the agent:\n{original_prompt}\n\n"
        f"Agent output:\n{agent_output}\n\n"
        f"Assertion to check: {assertion}"
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=judge_prompt)],
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="judge-user",
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text

    # Parse the JSON response
    try:
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "assertion": assertion,
                "passed": bool(result.get("passed", False)),
                "evidence": result.get("evidence", ""),
            }
    except (json.JSONDecodeError, AttributeError):
        pass

    # Default to fail if we can't parse the response
    return {
        "assertion": assertion,
        "passed": False,
        "evidence": f"Failed to parse judge response: {response_text[:200]}",
    }


async def run_all_evals(skill_dir: str, model: str, output_path: str, timeout: int = DEFAULT_TIMEOUT):
    """Main orchestration: run all evals, grade, compute metrics."""
    skill_data = parse_skill_md(Path(skill_dir))
    evals = load_evals(Path(skill_dir))

    all_results = []
    total_passed = 0
    total_assertions = 0

    for eval_case in evals:
        print(f"  Running eval {eval_case['id']}...", file=sys.stderr)

        result = await run_single_eval(
            eval_case, skill_data["instruction"], model, timeout
        )

        assertion_results = []
        for assertion in eval_case.get("assertions", []):
            grade = await grade_assertion(
                assertion, result["output"], eval_case["prompt"], model, timeout
            )
            assertion_results.append(grade)
            total_assertions += 1
            if grade["passed"]:
                total_passed += 1

        eval_passed = sum(1 for a in assertion_results if a["passed"])
        eval_total = len(assertion_results)
        eval_pass_rate = eval_passed / eval_total if eval_total else 0.0

        failed_assertions = [
            a["assertion"] for a in assertion_results if not a["passed"]
        ]

        all_results.append(
            {
                "eval_id": eval_case["id"],
                "output": result["output"],
                "passed": eval_passed,
                "total": eval_total,
                "pass_rate": eval_pass_rate,
                "failed_assertions": failed_assertions,
                "assertion_results": assertion_results,
            }
        )

        print(
            f"  Eval {eval_case['id']}: {eval_passed}/{eval_total} passed",
            file=sys.stderr,
        )

    overall_pass_rate = total_passed / total_assertions if total_assertions else 0.0

    metrics = {
        "pass_rate": overall_pass_rate,
        "passed": total_passed,
        "total": total_assertions,
        "per_eval": all_results,
    }

    Path(output_path).write_text(json.dumps(metrics, indent=2))

    # Print summary to stdout for the bash script to parse
    print(f"PASS_RATE={overall_pass_rate:.4f}")
    print(f"PASSED={total_passed}/{total_assertions}")


def main():
    parser = argparse.ArgumentParser(description="Run skill evals and produce metrics")
    parser.add_argument(
        "--skill-dir",
        required=True,
        help="Path to the skill directory containing SKILL.md and evals/",
    )
    parser.add_argument(
        "--model",
        default="openai/gpt-4o-mini",
        help="LiteLLM model string (e.g. openai/gpt-4o-mini, anthropic/claude-3-haiku-20240307)",
    )
    parser.add_argument(
        "--output",
        default="run.txt",
        help="Path to write the JSON metrics output",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("LITELLM_TIMEOUT", DEFAULT_TIMEOUT)),
        help=f"Timeout in seconds for LLM API calls (default: {DEFAULT_TIMEOUT}, or LITELLM_TIMEOUT env var)",
    )
    args = parser.parse_args()

    asyncio.run(run_all_evals(args.skill_dir, args.model, args.output, args.timeout))


if __name__ == "__main__":
    main()
