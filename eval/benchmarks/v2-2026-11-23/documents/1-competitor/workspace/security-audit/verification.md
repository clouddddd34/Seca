Sequential refutation and post-fix review

Expiry: independently re-read original-app.py.txt:39-51 and :54-65. Creation-time future validation and revocation filtering are strongest controls; neither checks elapsed time on read. Verdict: confirmed, supported by expired and exact-boundary failing tests.

Membership: re-read original-app.py.txt:28-51, :58, :74, :83. Identity is fetched fresh, but can_read ignores user tenant. Mutation/inventory protections cannot guard this sink. Owner and recipient migration both reproduce disclosure. Verdict: confirmed.

Post-fix adversarial pass: app/app.py:39-46 gates membership before owner shortcut, applies strict greater-than expiry, preserves revocation, and allows any independently live grant. Tests cover return migration and a fresh share after revocation. No new read or write path introduced. Do not treat synthetic authentication, storage, or trusted setup operations as vulnerabilities.

Coverage critic: all four business endpoints and four framework documentation/schema routes are mapped. Both mutation sinks and inventory response were traced. No workers, outbound clients, persistence, templates or duplicate application files found. No unresolved candidates. Sequential review is less independent than a separate reviewer; delegation explicitly prohibited.
