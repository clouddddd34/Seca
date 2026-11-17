# Evaluation protocol

The fixture verifies the harness, not the effectiveness of the skill. Never present passing fixture tests as a successful agent benchmark.

## Prepare fresh inputs

Build the Rust helper first. Obtain an unmodified checkout of the MIT-licensed [competitor](https://github.com/briiirussell/cybersecurity-skills) outside this repository; inspect its instructions and helpers before using them. Preparation records its commit and copies its license. It does not install or execute that project.

```sh
python eval/prepare.py --output /absolute/new-external-directory --competitor /absolute/competitor-checkout
```

On Windows, pass quoted Windows paths instead. Preparation creates three fresh copies for each of three arms: no explicitly invoked security skill, Seca, and upstream `owasp-audit`. All receive identical fixture files, Python packages, and the same optional `seca` executable. The compiler is not needed inside assessed workspaces. Competitor references and companion skills are retained to avoid silently breaking its workflow. No evaluator key, evaluator tests, or prior run results are copied.

`task.txt` is the common task, with only a skill invocation prefix varying. It requests assessment, evidence, fixes, and regression tests. All accounts and access rules are in the fixture README. The task is source-plus-local-runtime; it is not a URL-only benchmark. No desktop claims may be inferred from it.

## Execute

Use a fresh authenticated CLI session for each run, one model/version and reasoning configuration, the same tools, and the same 180-second wall-clock limit. The included runner uses Codex, ignores user config, does not persist sessions, applies workspace-write sandboxing, and stops the process tree on timeout. It explicitly selects the already-provisioned elevated Windows sandbox on Windows, disables web search and optional plugins by default, and leaves sandbox network access restricted. It executes sequentially in a rotated order. CLI versions must support the flags shown in `run.py`.

Run a small read/write/import preflight before spending model calls on a suite. On Windows, the supported sandbox probe below checks the existing sandbox without changing global configuration or bypassing managed requirements:

```powershell
$secaPython = (Get-Command python).Source
codex -c 'windows.sandbox="elevated"' sandbox --include-managed-config --permission-profile :workspace -- $secaPython -c "import fastapi, httpx; print('IMPORTS_OK')"
```

The sandbox must already be provisioned. If the preflight is denied, inspect the active configuration and policy rather than disabling isolation. The first Seca attempt failed because ignoring user configuration also omitted the Windows sandbox implementation; explicit selection passed both a direct sandbox check and an agent read/write/import preflight. See the official [Windows sandbox documentation](https://learn.chatgpt.com/docs/windows/windows-sandbox).

```sh
python eval/run.py /absolute/prepared-directory --model YOUR_AVAILABLE_MODEL --seconds 180
```

`protocol.json` locks the model request, reasoning effort, CLI version, time limit, and options for a prepared suite. Attempting to mix configurations is rejected. The manifest records fixture, task, skill-file, and helper hashes. Never edit assessed inputs or the skill while a suite is running.

This uses model access and may consume account credits. It never installs packages. For Claude comparisons, run the same prepared prompts in fresh Claude sessions with an equivalent budget; do not combine results from different models as though only the skill changed.

The workspace separation prevents accidental answer discovery through ordinary project searches. It is not an OS read-isolation boundary. Global instructions, installed skill metadata, authentication, and provider defaults can still influence the model. Inspect transcripts for contamination and record the client version, requested/actual model when available, reasoning setting, time limit, and any unavailable tools. Do not claim a fully blinded baseline if you cannot establish it. Classify transport/authentication failures as invalid runs, not zero-quality skill results. Prepare fresh workspaces before rerunning; do not reuse patched code.

## Score

After each run, read its transcript and report from the evaluator context. Use `answer_key.md` for scoring, then run:

```sh
python eval/check_patch.py /absolute/prepared-directory/1-seca/workspace/app/app.py
```

The patch checker is intentionally not available to assessed agents. Its narrow checks are supporting evidence; inspect patches for hardcoded answers, deleted behavior, and tests that merely mirror the implementation. Score discovery, false accusations, proof quality, access-rule compliance, fixes, and coverage separately. Record timed-out or incomplete work honestly. Three runs per arm on one small fixture provide preliminary results only.

Local harness checks:

```sh
cargo build --locked
cargo test --locked
python -m unittest eval.test_fixture eval.test_tools eval.test_evaluation eval.test_e2e -v
```

## Separate URL-only smoke check

After source-based evaluation, this runner supplies only the installed skill, a local fixture URL, and bounded read-only authorization. It starts a temporary loopback server, records requests and created orders, then stops it. It uses the same Codex sandbox options and medium reasoning. Use a new output directory outside this repository; this consumes a model call and requires the already-installed fixture packages.

```sh
python eval/url_smoke.py /absolute/new-url-check-directory --model YOUR_AVAILABLE_MODEL --seconds 180
```

Inspect `observations.json`, `execution.json`, and the report together. A successful simple-page check does not establish authenticated coverage or behavior on a rich website. Keep post-change checks separate from the frozen comparative results. The [2026-11-18 results](RESULTS.md) include one URL-only check and one targeted source-based follow-up; neither was added to the original nine-run scores.
