# Sequential verification and post-fix review
Delegation prohibited by user: verification used separate source re-derivation steps in the same context, not an independent agent.

Expired-share claim: re-read original app/app.py:39-52 and :55-64. Strongest controls are recipient match, revoked flag and future-at-creation validation. A valid share can later expire without revocation. There is no clock comparison on GET. Bob's a request returns the full document after expiry. Confirmed by two failing assertions (past and exact deadline).

Membership claim: independently re-read original read path and sharing/revocation guards. The user object is resolved afresh but unused by can_read; owner fast path and share path both skip tenant. Neither mutation guard applies to GET. README explicitly authorizes trusted migration and requires current membership separately from ownership/sharing. Confirmed by owner and recipient migration failures. Trusted setup is not itself the vulnerability.

Post-fix adversarial review: tenant guard precedes BOTH authorization alternatives; strict expiry predicate rejects equality; revoked still rejects; any live matching share suffices even alongside expired grants. No new exemption, route or mutation introduced. Current-tenant owner bypass of expiry is intentional ownership access. Mutations and inventory unchanged. All ten tests pass. No claim of independent-model review.

Coverage critic: enumerated eight routes (four business plus four metadata) in surface-checks.json and matched them to ledger. Inspected all 85 original source lines and both mutation siblings. No hidden jobs, upload handlers, persistence or network sinks. Added metadata and parser units; no remaining unmapped route. Out-of-scope cryptographic/dependency/deployment assurance justified by README and user restrictions. Candidate unit remains candidate after fixes. No candidate lacks a verdict.

Fixture exclusions: fake credentials/auth mapping, memory-only state, absent deployment are excluded conditions, not production findings. No other test/generated/vendor/doc candidate was promoted. Scope counts represent conditions, not vulnerabilities.
