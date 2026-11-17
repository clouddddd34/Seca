# Research and design decisions

Reviewed on 2026-11-18. Repository observations describe inspected instructions, not measured effectiveness.

| Source | Observation | Decision for Seca |
| --- | --- | --- |
| [cybersecurity-skills OWASP audit](https://github.com/briiirussell/cybersecurity-skills/blob/18642b272e9fe57ed6bdf3fd96614915e8a4d71d/skills/owasp-audit/SKILL.md) | Already includes verification, coverage ledgers, and report validation | Do not claim these features are unique; include it as a benchmark arm |
| [Claude-Red](https://github.com/SnailSploit/Claude-Red) | Offers a broad collection of offensive skills | Keep our initial implementation focused on builder-owned web/API assessments |
| [Anthropic security review](https://github.com/anthropics/claude-code-security-review) | Reviews code changes and filters false positives; README documents prompt-injection limitations | Treat target material as evidence, not authority; do not claim textual safeguards guarantee isolation |
| [OWASP ASVS](https://asvs.owasp.org/) | Defines web application security requirements | Use relevant, versioned control references instead of copying an entire checklist |
| [OWASP WSTG](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/) | Provides testing procedures | Choose checks based on the actual surface and permitted scope |
| [Electron security](https://www.electronjs.org/docs/latest/tutorial/security), [Tauri security](https://v2.tauri.app/security/) | Desktop frameworks have distinct privilege and process boundaries | Defer desktop guidance until we have a representative fixture |
| [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/) | Supports in-process HTTP testing with TestClient | Use deterministic fake-data fixture checks without external targets |
| [reqwest client configuration](https://docs.rs/reqwest/0.13.5/reqwest/blocking/struct.ClientBuilder.html) | Exposes timeout, redirect, proxy, retry, and TLS controls | Bound replay requests and preserve certificate validation |

License review: the inspected [cybersecurity-skills](https://github.com/briiirussell/cybersecurity-skills/blob/18642b272e9fe57ed6bdf3fd96614915e8a4d71d/LICENSE), [Claude-Red](https://github.com/SnailSploit/Claude-Red/blob/main/LICENSE), and [Anthropic reviewer](https://github.com/anthropics/claude-code-security-review/blob/main/LICENSE) license files use MIT terms. No competitor implementation or skill text is copied into Seca's distributed skill. The benchmark preparation copies the competitor's own notices into its isolated evaluation workspace. Credit here acknowledges research, not an endorsement or measured superiority.

The first fixture exercises source-plus-runtime authorization and price integrity. It cannot establish broad OWASP coverage, production safety, URL-only effectiveness, desktop coverage, or resistance to prompt injection. Those need separate evaluations.
