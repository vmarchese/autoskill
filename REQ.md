Your task is to implement an automatic Skill optimizer inspired by Karpathy's autoresearch loop (https://github.com/karpathy/autoresearch), not for the training of an LLM but for the optimization of a SKILL (https://agentskills.io/home)

The repository must be structured as follows:

```
+-- skill/  # the skill folder
|     +-- skill_name/ # the skill to be optimized, you can modify ONLY the files in this folder
|             +--- SKILL.md # the skill instructions and other files
|             +--- ...
|             +--- evals/ # the folder containing the evaluation dataset
+-- skill_runner.py # the skill runner. This file MUST NEVER BE TOUCHED
+-- optimizer_loop.sh # the optimizer loop as a bash script
+-- instructions.md # the claude code instructions for the skill changes
```

At each run the loop the optimizer should:

1. Run claude code in non-interactive mode to examine the SKILL.md and propose changes
2. implement the changes in the SKILL
3. log the changes done in a "memory-<runid>.txt" file
3. Run the skill on the evals dataset
4. Save the metrics in a `run.txt` file
5. If the metrics are better than the previous run in the loop:
   5.1 commit the changes with `git commit`
6. If the metrics are worse
   6.1 revert back the changes (`git stash` or equivalent)
7. in both cases log the result in the memory file

#  Guidelines
- Implement the skill runner according to the agent skills specs in https://agentskills.io/home 
- For the agent that runs the skills in the skill runner, use Google's ADK (https://google.github.io/adk-docs/) in python
- The agent LLM model should be configurable (e.g. OpenAI, Anthropic, ...)
- implement the optimizer loop as described above
- implement the instructions.md file to instruct claude code to optimize the skill
- for the loop convergence logic consider the following: 
  - set a configurable max number of iterations for the loop
  - if the metric has not moved for a number of iterations before the current, stop the loop (convergence reached)

- Keep the code clean and readable
- modify the README.md file with the documentation

