# Assessment log
Scope: app/ only, source review and in-process FastAPI TestClient. No network,
external services, package installation, or delegated work. Maximum five orders
per fresh instance. Rules: app/README.md supplied by user.

Stack: FastAPI/Pydantic, static bearer identities, in-memory orders. Middleware
protects private routes and admin prefix; invoice/report handlers cross object
trust boundaries; purchase crosses client/server pricing boundary.

Candidates: F-001 invoice ownership; F-002 report tenant isolation; F-003 pricing.
Next: reproduce with assertions, patch handlers, rerun authorization matrix.
Dependency advisories unavailable within no-external-services scope.

Completed: three candidates confirmed by runtime response relationship checks and
independent persisted-order reads; focused fixes applied and retested. Five test
methods pass; original suite had 11 failing subtests. Evidence-before/after JSON
records environment and source hashes. report.md contains findings, full matrix,
coverage, and gaps. No unresolved candidate requiring further exploitation.
Remaining uncertainty: dependency advisories, production transport/proxy behavior,
concurrency/resource limits, exhaustive normalization and credential lifecycle.
