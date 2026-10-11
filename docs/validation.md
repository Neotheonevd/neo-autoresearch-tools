# v0.1.1 release validation

Local verification date: 2026-10-11.

- Python 3.12 / Windows: 38 offline unit and local HTTP tests passed.
- Actual AutoSOTA 0.2.0 CLI: Linux container dry-run with networking disabled,
  no model credentials, CPython 3.11 runtime; generated an actual master prompt
  and exited successfully. This was not a paid optimization run.
- Source distribution: explicit allowlist, per-file SHA256 manifest, private-path
  and credential-pattern checks. Runtime and research datasets are excluded.
- GitHub Windows/Linux Python 3.11/3.12 workflow is configured but has not yet
  run on GitHub. Configuring CI does not establish those platform results.

Not yet certified: paid Argus → AutoSOTA → evaluator → Argus closure, extended
thinking / full Claude SDK compatibility, and reboot service recovery.

The separate live research project has completed attribution evaluations, but
those runs do not constitute this integration package's end-to-end acceptance.
Its most recent gain came primarily from agent/event ownership correction;
it is not evidence that candidate explanation comparison independently improved
attribution. No benchmark improvement or SOTA claim is made for this tool release.
