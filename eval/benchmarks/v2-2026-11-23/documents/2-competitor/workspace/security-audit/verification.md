# Sequential per-finding refutation (before fixes)

Tenant candidate: re-read app/app.py:28-51 and sibling controls :58-60, :74-83. Authentication resolves the current user record, but can_read never consults that record. Strongest read guard is owner identity or matching nonrevoked share; neither enforces current tenant membership. Creation and revoke tenant checks apply only to mutations, not reads. A trusted migration is a prerequisite, not attacker-accessible state mutation. Confirmed: a migrated owner or recipient receives full original-tenant document JSON, as shown by two 200 != 404 failures in before-tests.txt. Scope is previously owned/shared documents, not arbitrary documents.

Expiry candidate: independently re-read app/app.py:39-51 and :60-65. Creation rejects past timestamps, but elapsed time does not mutate revoked, and no scheduled expiry mechanism exists. Strongest control is not-revoked; this cannot substitute for expires_at. Confirmed: a recipient receives the document at or after expiration (two 200 != 404 failures). Owner access must remain independent of share expiry. Document and recipient matching and revocation must be retained.

Negative candidates: recipient resharing and revoking another owner's share are denied by owner checks; current-tenant admin filtering holds even after migration. These controls are exercised by the regression suite. Fixture identity mechanism, synthetic storage and absent deployment configuration excluded under explicit README rules (three fixture-condition groups); no production authentication claim inferred.

Review is sequential, not an independent model/agent review, per user prohibition on delegation.
