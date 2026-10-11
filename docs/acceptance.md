# Acceptance gates

## Offline correctness

Run all tests. Verify persistent budget stops, category isolation, conservative
unknowns, actual child timeout termination, no crash replay, single writer,
protected evaluators, fixed denominators, guardrails, protocol tool identities,
source-only export and actual upstream CLI dry-run.

Offline fixture scores are synthetic and never research results. Dry-run must
produce AutoSOTA's actual master prompt, not just exit with code zero.

## Paid integration (not yet certified)

1. Verify current Argus and AutoSOTA versions, native credentials/terms and exact
   sandbox. A doctor/help success is not a model or SDK compatibility test.
2. Route every backend call through the shared category budgets. Verify one
   genuine tool-call/result/continuation cycle, including provider usage.
3. Freeze one inexpensive real research task and its evaluator. Observe Argus
   submit it, AutoSOTA modify code, evaluate the same protocol, return a patch and
   full evidence, and native Argus consume that evidence to select next work.
4. Interrupt at safe boundaries and test native resume without repeated paid
   calls. Separately inject budget exhaustion and verify the backend actually
   stops rather than invoking planning/self-maintenance into a closed gate.
5. Complete two successive bounded batches, with all settings, negative results,
   costs, regressions, outstanding questions and review recorded.

Only after these receipts exist is the configuration ready for a longer
unattended research window. Success on a development benchmark is still not an
independent test result or a SOTA claim.

## Current research incident

The initial native Argus window reached its research category budget during
planning, before producing a full optimization candidate. Native planning and
self-maintenance continued encountering rejected gateway requests. The daemon
was drained and stopped, with evidence preserved and no budget increase.

This motivates category allocations, process-level stop on persistent pause,
bounded optimization handoffs and no duplicate independent planners. It is a
workflow failure, not evidence that the attribution method improved or failed.

## Release readiness

Verify source manifest, tests, portability, upstream references, no provider keys,
private paths, gold labels, transcripts, datasets or third-party binaries. Publish
only the standalone source folder, never the surrounding research workspace.
