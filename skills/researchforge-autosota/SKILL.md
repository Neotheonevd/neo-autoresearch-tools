---
name: researchforge-autosota
description: Delegate a bounded code optimization batch from native Argus to actual AutoSOTA and import its artifacts.
---

Keep native Argus in charge of research planning. This skill is an optimization
tool, not a replacement planner or an additional indefinite research loop.

1. Read the operator's fixed protocol, budget and previous paired outcomes. Pick
   one general mechanism hypothesis. Reuse the currently best frozen source.
   Native Planner reads a compact experiment summary, not entire184-case JSON
   transcripts. Delegate bulk error statistics to code execution and keep only
   decision-sized evidence in model context. Planning has its own hard category
   budget; don't spend the optimization allowance just planning experiments.
2. Create an owned copy of the method repository and a separate batch workspace.
   Never overlap an active writer. Write a task contract following
   `docs/task.example.json`. Protect scorer files by host-recorded hashes.
3. Run `python -m researchforge plan TASK LAUNCHERS --root ROOT` and inspect the
   exact argv. Use the installed and version-checked AutoSOTA CLI; never replace
   it with a prompt telling another agent to imitate AutoSOTA.
4. Submit once: `python -m researchforge --state STATE submit TASK --root ROOT`.
   Execute the bounded batch once with `worker LAUNCHERS --root ROOT`. Keep this
   tool call alive until completion; do not spend model turns polling it.
5. Import actual AutoSOTA `scores.jsonl`, patches and evaluation verdict via
   `collect WORKSPACE`. Read `backend_receipt.json`; its scores are backend claims,
   not automatically the shared evaluator's official results.
6. Verify complete fixed-denominator results, paired gains AND regressions,
   unchanged scorer and mechanism adoption. Record settings and research findings.
   An exit code, a better explanation or a larger Agent metric is not sufficient.
7. Let native Argus review and plan the next bounded batch. Do not duplicate a
   full AutoSOTA review just for ceremony; check the actual evidence and remaining
   contract gaps. Promote only after explicit fixed-protocol acceptance.

Budget exhaustion or unknown billing must pause the project and stop its backend
process. Do not generate self-maintenance/replanning calls into a closed gateway.
Do not start another window, reset budgets, rerun paid failures, switch models,
or change scope to recover from a pause. Native resume requires reconciled receipts.

No credentials in tasks, source, arguments or public logs. Real provider keys
belong only to the host gateway. The operator must configure a verified sandbox
for the CLI launcher; this skill and working-directory ownership are not sandboxes.
