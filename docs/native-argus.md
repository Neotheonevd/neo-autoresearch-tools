# Native Argus configuration

Use a fresh, nonoverlapping owned project. Preserve the native state schema;
configure through Argus's supported environment/CLI, never edit its task state.

```sh
export ARGUS_SKILL_HOME="/path/to/private-argus-state"
export ARGUS_SKILL_RUNNER_BACKEND=pi
export ARGUS_SKILL_MODEL=research/deepseek-v4-pro
export ARGUS_SKILL_MANAGER_MODEL=research/deepseek-v4-pro
export ARGUS_SKILL_PLAN_MODEL=research/deepseek-v4-pro
export ARGUS_SKILL_ENGINEER_MODEL=research/deepseek-v4-pro
export ARGUS_SKILL_REVIEWER_MODEL=research/deepseek-v4-pro
export ARGUS_SKILL_MAX_ROUNDS=6
export ARGUS_SKILL_REQUIRE_POST_TASK_LEARNING=0
export ARGUS_SKILL_AUTOCOMMIT_SKILLS=off
argus doctor
argus --continuous --bounded --mission-width 1 --objective-file OBJECTIVE.md --daemon-fg
```

The sample paths are placeholders. Set verified container CLI wrappers via
`ARGUS_SKILL_MANAGER_RUNNER_BIN`, `ARGUS_SKILL_PLANNER_RUNNER_BIN`,
`ARGUS_SKILL_ENGINEER_RUNNER_BIN`, and `ARGUS_SKILL_REVIEWER_RUNNER_BIN`.
Use category-specific local proxy tokens in each wrapper. Never put the real
upstream key in the wrapper's environment. The persistent model gateway and
worker must run under the host's service manager for reboot recovery; bare
terminal sessions are not advertised as durable services.

Use foreground mode under the worker when its budget-stop control is required;
do not launch a detached daemon that can outlive its enclosing job unnoticed.
The initial existing Who&When daemon was a separate project and was explicitly
stopped at its original budget. This example does not resume or enlarge it.

The native planner gets: research direction, best source ID, compact scoreboard,
top general error categories, remaining budget and last batch's mechanism finding.
AutoSOTA gets: the owned repository, bounded hypothesis, fixed evaluator, prior
negative findings and allowed edit scope. Native Argus consumes AutoSOTA's actual
artifact receipt after the optimization batch, not every small code edit.

Keep native Needs-you questions visible. Reversible implementation within the
frozen contract is delegated; scope, budget, credential, data-access or publication
changes require the operator. No imitation of an operator answer is permitted.
