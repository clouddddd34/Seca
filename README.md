# Seca

**Find security issues you can reproduce, understand, and fix.**

Seca is a reusable Markdown skill for AI coding agents reviewing authorized websites and APIs, with optional Rust helpers and a deliberately vulnerable Python/FastAPI evaluation fixture. It guides an agent through scope, access rules, verification, remediation, and coverage reporting.

**Status: early prototype.** Local fixture and helper tests pass on Windows. The comparative agent benchmark has not produced valid results; see [validation results](eval/RESULTS.md). There is no claim that Seca outperforms existing skills. Desktop application guidance is deferred until there is a desktop fixture.

## What you get

| Component | Purpose |
| --- | --- |
| [security-audit/SKILL.md](security-audit/SKILL.md) | Portable web/API assessment instructions |
| [Access rules](security-audit/references/access-rules.md) | Define who may access which resources |
| [Evidence guidance](security-audit/references/evidence.md) | Separate confirmed, likely, and unverified findings |
| [Rust CLI](tools/seca/main.rs) | Bounded bearer-token request replay and JSON ledger validation |
| [Finding template](security-audit/assets/finding.json) | A consistent record of evidence and uncertainty |
| [Local fixture](eval/fixture/README.md) | Fake-data application for evaluation |

The skill works without the CLI. A URL alone supports a limited unauthenticated review; source, test accounts, and access rules enable deeper checks. The implementation language does not limit the language of applications being assessed.

## Install the skill

Clone this repository, then copy the entire `security-audit` folder into your coding agent's project skill directory. Do not copy just `SKILL.md`; it references supporting files. Use one destination for the chosen agent and do not overwrite an existing same-name skill without reviewing it.

| Agent | Project destination | Invocation |
| --- | --- | --- |
| Codex | `.agents/skills/security-audit/` | `$security-audit` |
| Claude Code | `.claude/skills/security-audit/` | `/security-audit` |

For example, from the root of the project you want to assess, using PowerShell:

```powershell
$secaSkillSource = 'C:\path\to\Seca\security-audit'
$secaSkillDestination = '.agents/skills/security-audit' # Use .claude/skills/security-audit for Claude Code
if (Test-Path -LiteralPath $secaSkillDestination) { throw 'Review the existing skill before replacing it.' }
New-Item -ItemType Directory -Path (Split-Path $secaSkillDestination) -Force | Out-Null
Copy-Item -LiteralPath $secaSkillSource -Destination $secaSkillDestination -Recurse
```

On macOS/Linux, create the chosen parent directory and copy the folder with `cp -R /path/to/Seca/security-audit .agents/skills/` (or `.claude/skills/`). Start a new agent session and confirm it can discover the skill. If your client uses a different skill location, follow its documentation or explicitly ask it to read this repository's `security-audit/SKILL.md`.

These locations follow the official [Codex](https://learn.chatgpt.com/docs/build-skills) and [Claude Code](https://code.claude.com/docs/en/skills) guides. Agent/runtime compatibility has not been exhaustively tested.

## Example prompts

```text
Use $security-audit to review this repository and its local API.
I own the application. Start with non-mutating checks, verify findings,
and report what you could not test. Ask before changing source code.
```

```text
Use /security-audit for http://127.0.0.1:8765, my local test application.
Only this origin is in scope. Start with an unauthenticated, non-mutating
review and explain which checks need test accounts or source access.
```

```text
Use $security-audit to verify the authorization issue described here.
The supplied test accounts and access matrix define the allowed behavior.
Reproduce locally, apply a focused fix, and test both the denied case
and legitimate access. Keep evidence redacted.
```

## Build optional Rust helpers

Requires Rust 1.93+ and the platform's Rust linker/build dependencies. The initial build downloads crates; ask before installing tools or packages in a managed environment. `Cargo.lock` records the resolved dependency versions.

```sh
cargo build --release --locked
```

Run `target/release/seca` (`target\release\seca.exe` on Windows). To make `seca` available on PATH, optionally use `cargo install --path . --locked`. The compiled helper does not require Python; Python is needed only for the fixture and evaluation scripts. Build separately for each target OS; only the Windows build has been exercised here.

With the local fixture running, PowerShell example:

```powershell
$env:SECA_BOB_TOKEN = 'fixture-bob'
$env:SECA_ALICE_TOKEN = 'fixture-alice'
.\target\release\seca.exe replay examples/replay.json replay-report.json --authorized
```

For macOS/Linux:

```sh
SECA_BOB_TOKEN=fixture-bob SECA_ALICE_TOKEN=fixture-alice \
  ./target/release/seca replay examples/replay.json replay-report.json --authorized
```

The example checks Bob's invoice with its owner, another user, and anonymous access. Its expected denial status is illustrative: a 404 can also be a valid denial. Inspect response meaning and the access rule; do not equate any status mismatch with a security bug.

Replay is GET-only, accepts 1–8 accounts, uses independent bearer headers, follows no redirects, and performs no retries. Remote targets require HTTPS and `--allow-remote` in addition to established permission. **All development testing for this project uses local fixtures only.** It does not automate login, browser cookies, active scanning, or state-changing requests. See [helper behavior and limits](security-audit/references/helpers.md).

Reports omit raw URLs, bodies, headers, and token values. They contain observations rather than vulnerability verdicts. Keep a separately redacted reproduction and relevant revision/environment. Do not place real credentials in configs, reports, or source control.

## Findings log

Copy the [template](security-audit/assets/finding.json) into your assessment workspace and replace its example text with actual observations. Using the installed CLI:

```sh
seca log-init audit.json "local application" "source and local checks"
seca log-add audit.json finding.json audit-next.json
seca log-check audit-next.json
```

Each addition writes a new ledger version and preserves its input. Confirmed findings require evidence and reproduction steps, but structural validation cannot establish that those claims are true. Arbitrary findings text is not automatically scrubbed of secrets. Exclude real assessment artifacts from public repositories.

## Develop and evaluate

The fixture requires Python 3.11+ and the versions in `eval/fixture/requirements.txt`. Use an isolated environment; if packages are missing and installation is authorized, run `python -m pip install -r eval/fixture/requirements.txt`. Then:

```sh
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
cargo build --locked
cargo test --locked
python -m unittest eval.test_fixture eval.test_tools eval.test_evaluation eval.test_e2e -v
```

Follow the [fixture instructions](eval/fixture/README.md) to run the local app. Follow the [evaluation protocol](eval/README.md) to compare no explicitly invoked skill, Seca, and the upstream OWASP audit. Evaluator answers stay outside the assessed workspaces. Passing harness tests does not establish agent assessment quality.

## Research and license

See [research and credits](docs/RESEARCH.md) for sources and design decisions. Seca's original code and instructions are MIT-licensed. Upstream competitor material is not vendored in this repository; evaluation preparation preserves its license when copying it into temporary workspaces. Dependencies retain their own licenses.
