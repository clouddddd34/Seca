# Assessment log

Scope: only app/ source and in-process FastAPI TestClient requests, synthetic fixture accounts. No network, package installation, other software scans, or delegated work. Maximum five orders per fresh create_app() instance.

Requirements: app/README.md. Assigned guidance: assigned-skill/SKILL.md and references/access-rules.md, references/evidence.md. No other skills used.

Attack surface: FastAPI authentication/admin middleware; public root/health; authenticated identity, invoice, report, catalog, order and admin export routes; authenticated default OpenAPI route. Static bearer fixtures map to identities; in-memory dictionaries and orders; no database or external integrations.

Access matrix: anonymous may access root/health only; invoice owner alone may read invoice (admin has no exception); report tenant members may read reports; admin alone may export; users list their own orders; catalog determines totals. Rules are explicit README requirements.

Initial hypotheses: invoice tenant-only check violates ownership; report lookup lacks tenant check; purchase trusts supplied price. Admin restriction appears enforced in middleware and needs a negative control. Verification and remediation pending.

Completed: all three hypotheses confirmed by bounded local requests and regression failures, then fixed and retested. Structured records F-001.json through F-003.json derive from the assigned template. Before/after evidence includes source fingerprints and resolved versions. Five regression methods now pass; admin and authentication negative controls pass. At most three orders per instance; evidence capture creates one per separate instance. Report contains access coverage and remaining uncertainty. No outstanding remediation for confirmed findings. Dependency advisory review, deployment, concurrency, browser and transport testing remain outside this assessment.
