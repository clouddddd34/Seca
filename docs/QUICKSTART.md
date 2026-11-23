# Try Seca locally

The skill works without Rust or Python. The optional executable handles bounded
bearer-token GET comparisons and structured findings; it is not a general scanner.

1. Extract `seca-skill-v0.1.0-rc.1.zip` and copy its complete `security-audit/` folder
   into your project's `.agents/skills/` (Codex) or `.claude/skills/` (Claude Code).
   Review an existing same-name folder before replacing it. Start a fresh session;
   if skill discovery differs in your client, explicitly ask it to read SKILL.md.
2. Supply the local repository or authorized test URL, allowed actions, and any test
   accounts/access rules. Use synthetic data. A URL alone permits much less coverage
   than source plus accounts; the report should say what was not tested.
3. Request the result you need. For example:

```text
Use $security-audit on this local repository. I own it and authorize source review,
local synthetic reproductions, focused fixes, and regression tests. Do not contact
deployed services. Report actual evidence, protected behavior, and coverage gaps.
```

For Claude Code use `/security-audit`. For a read-only URL assessment:

```text
Use $security-audit on http://127.0.0.1:8765/. I own this local service. Only this
origin and linked first-party resources are in scope. Start with non-mutating checks.
No accounts are available. Report what you can verify and what remains blocked.
```

To reproduce the project's development checks, follow the repository README and
[benchmark v2 instructions](../eval/v2/README.md). Those require Python dependencies
and Rust, unlike skill-only use. The fixture applications deliberately include bugs;
they are local evaluation material, not deployment templates.

The Windows CLI archive includes `seca.exe` and `HELPERS.md`. Verify its SHA-256
against `SHA256SUMS.txt` with `Get-FileHash -Algorithm SHA256`, extract it to a chosen
tools directory, and invoke it by path. It needs no Python runtime. The binary is
unsigned, and this release candidate does not include validated macOS/Linux binaries.
