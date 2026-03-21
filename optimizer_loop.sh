#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Configuration (override via environment variables)
# ============================================================
SKILL_DIR="${SKILL_DIR:-skill/event-extractor}"
MODEL="${MODEL:-openai/gpt-4o-mini}"
MAX_ITERATIONS="${MAX_ITERATIONS:-20}"
PATIENCE="${PATIENCE:-3}"

# ============================================================
# Setup
# ============================================================
RUN_ID="$(date +%Y%m%d_%H%M%S)"
MEMORY_FILE="runs/memory-${RUN_ID}.txt"
METRICS_FILE="run.txt"
SNAPSHOT_DIR="runs/snapshots-${RUN_ID}"

mkdir -p runs "$SNAPSHOT_DIR"
source .venv/bin/activate

# ============================================================
# Backup the original skill before any modifications
# ============================================================
cp -r "$SKILL_DIR" "$SNAPSHOT_DIR/iter-0-original"
echo "Original skill backed up to ${SNAPSHOT_DIR}/iter-0-original"

# Keep a copy of the "best" skill to restore from on revert
BEST_SNAPSHOT="$SNAPSHOT_DIR/iter-0-original"

# ============================================================
# Helper: format per-eval results from metrics JSON into memory
# ============================================================
format_per_eval() {
    python3 -c "
import json, sys
data = json.load(open('${METRICS_FILE}'))
for e in data['per_eval']:
    failed = e.get('failed_assertions', [])
    fail_str = ''
    if failed:
        fail_str = ' [' + ', '.join(f'FAIL: \"{a}\"' for a in failed) + ']'
    print(f\"  eval {e['eval_id']}: {e['passed']}/{e['total']} passed{fail_str}\")
"
}

# ============================================================
# Header
# ============================================================
{
    echo "=== AUTOSKILL OPTIMIZER ==="
    echo "run_id: ${RUN_ID}"
    echo "skill: ${SKILL_DIR}"
    echo "model: ${MODEL}"
    echo "max_iterations: ${MAX_ITERATIONS}"
    echo "patience: ${PATIENCE}"
    echo ""
} | tee "$MEMORY_FILE"

best_pass_rate="0.0"
stale_count=0

# ============================================================
# Iteration 0: Baseline
# ============================================================
echo "[Baseline] Running initial eval..." | tee -a "$MEMORY_FILE"

python skill_runner.py --skill-dir "$SKILL_DIR" --model "$MODEL" --output "$METRICS_FILE"

baseline=$(python3 -c "import json; print(f\"{json.load(open('${METRICS_FILE}'))['pass_rate']:.4f}\")")
baseline_passed=$(python3 -c "import json; d=json.load(open('${METRICS_FILE}')); print(f\"{d['passed']}/{d['total']}\")")
best_pass_rate="$baseline"

{
    echo ""
    echo "--- ITERATION 0 (BASELINE) ---"
    echo "pass_rate: ${baseline}"
    echo "passed: ${baseline_passed}"
    echo "status: BASELINE"
    echo "per_eval:"
    format_per_eval
    echo ""
} | tee -a "$MEMORY_FILE"

echo "Baseline pass_rate: ${baseline}"
echo ""

# ============================================================
# Main Loop
# ============================================================
for iteration in $(seq 1 "$MAX_ITERATIONS"); do
    echo "========================================"
    echo "[Iteration ${iteration}/${MAX_ITERATIONS}]"
    echo "========================================"

    # Step 1: Invoke Claude Code to propose and implement changes
    export MEMORY_FILE
    export SKILL_DIR
    claude_output=$(claude --print --dangerously-skip-permissions \
        "Read instructions.md and follow the instructions there. The skill directory is ${SKILL_DIR}. The memory file is at ${MEMORY_FILE}. Current iteration: ${iteration}/${MAX_ITERATIONS}. Best pass_rate so far: ${best_pass_rate}." 2>/dev/null || echo "CHANGES: claude code invocation failed")

    # Extract change description
    changes=$(echo "$claude_output" | grep "^CHANGES:" | head -1 || echo "CHANGES: no description provided")
    changes_desc="${changes#CHANGES: }"
    echo "Changes: ${changes_desc}"

    # Step 2: Run evals
    echo "Running evals..."
    python skill_runner.py --skill-dir "$SKILL_DIR" --model "$MODEL" --output "$METRICS_FILE"

    current_pass_rate=$(python3 -c "import json; print(f\"{json.load(open('${METRICS_FILE}'))['pass_rate']:.4f}\")")
    current_passed=$(python3 -c "import json; d=json.load(open('${METRICS_FILE}')); print(f\"{d['passed']}/{d['total']}\")")
    echo "pass_rate: ${current_pass_rate} (best: ${best_pass_rate})"

    # Step 3: Save snapshot of this iteration's skill
    iter_snapshot="$SNAPSHOT_DIR/iter-${iteration}"
    cp -r "$SKILL_DIR" "$iter_snapshot"

    # Step 4: Compare and decide
    improved=$(python3 -c "print('yes' if float('${current_pass_rate}') > float('${best_pass_rate}') else 'no')")

    if [ "$improved" = "yes" ]; then
        echo "IMPROVED! Keeping changes."
        best_pass_rate="$current_pass_rate"
        stale_count=0
        BEST_SNAPSHOT="$iter_snapshot"
        status="IMPROVED (kept)"
    else
        echo "No improvement. Reverting to best skill."
        stale_count=$((stale_count + 1))
        # Restore skill from best snapshot (preserve evals, only restore SKILL.md)
        rm -rf "$SKILL_DIR"
        cp -r "$BEST_SNAPSHOT" "$SKILL_DIR"
        status="REVERTED (no improvement)"
    fi

    # Step 5: Write iteration to memory file
    {
        echo "--- ITERATION ${iteration} ---"
        echo "changes: ${changes_desc}"
        echo "pass_rate: ${current_pass_rate}"
        echo "passed: ${current_passed}"
        echo "status: ${status}"
        echo "snapshot: ${iter_snapshot}"
        echo "per_eval:"
        format_per_eval
        echo "stale_count: ${stale_count}/${PATIENCE}"
        echo ""
    } >> "$MEMORY_FILE"

    echo "stale_count: ${stale_count}/${PATIENCE}"
    echo ""

    # Step 6: Check for perfect score
    if [ "$improved" = "yes" ] && python3 -c "exit(0 if float('${current_pass_rate}') >= 1.0 else 1)"; then
        echo "Perfect score! All assertions passed."
        {
            echo "=== PERFECT SCORE ==="
            echo "All evals passed at iteration ${iteration}. Stopping."
        } >> "$MEMORY_FILE"
        break
    fi

    # Step 7: Check convergence
    if [ "$stale_count" -ge "$PATIENCE" ]; then
        echo "Convergence reached: no improvement for ${PATIENCE} consecutive iterations."
        {
            echo "=== CONVERGENCE REACHED ==="
            echo "Stopped after ${iteration} iterations (no improvement for ${PATIENCE} consecutive iterations)"
        } >> "$MEMORY_FILE"
        break
    fi
done

# ============================================================
# Summary
# ============================================================
{
    echo ""
    echo "=== OPTIMIZATION COMPLETE ==="
    echo "Final best pass_rate: ${best_pass_rate}"
    echo "Best snapshot: ${BEST_SNAPSHOT}"
    echo "Optimized skill: ${SKILL_DIR}"
} | tee -a "$MEMORY_FILE"

echo ""
echo "Memory log: ${MEMORY_FILE}"
echo "Snapshots: ${SNAPSHOT_DIR}"
echo "Latest metrics: ${METRICS_FILE}"
