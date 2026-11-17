# Local application security assessment

Assessed on 2026-11-18 using the assigned security-audit skill. Three findings
were **confirmed by local runtime reproduction**, fixed, and retested. This is
a bounded assessment of a fake-data training app, not a comprehensive pentest
or assurance that a deployed application would be secure.

## Scope and method

Reviewed all source in app/app.py, app/run.py, requirements.txt, and the intended
rules in app/README.md. Used installed packages and in-process FastAPI TestClient;
no listener, external services, installations, other software scans, or agents.
Each test gets a fresh application. At most two fake orders were created in any
instance; the separate minimal reproduction creates one. State disappears with
the instance. No real payments or sensitive data were involved.

Reviewed authentication, object authorization, tenant isolation, administrative
access, input validation, and business logic, following ASVS/WSTG topic areas.
No version-specific control IDs or current advisory claims are made: external
guidance/advisories were not fetched under the no-external-contact constraint.

## Confirmed findings

Severity describes the analogous application impact; all demonstrated data and
transactions here are synthetic. Confidence is high for all three findings.

### F-001 — Invoice ownership boundary missing (medium)

**Expected:** README makes invoices private to their owner, even within a tenant;
admin has no exception. **Observed:** Alice could read Bob's invoice, and north
admin could read both north members' invoices. Cross-tenant access was already
blocked. Preconditions: a valid fixture identity and a same-tenant invoice ID.

**Trace:** identity middleware authenticates the caller, then invoice() originally
checked only tenant equality before returning the complete invoice. No upstream
owner check existed. **Reproduction:** as Alice, GET /invoices/inv-b returned 200
with Bob's owner field; Alice's own invoice returned 200 as a legitimate control.
The full four-identity/three-invoice matrix produced four unauthorized successes.
This demonstrates unauthorized invoice disclosure, not mutation or account takeover.

**Fix applied and verified:** invoice() now requires both matching tenant and
owner. Unauthorized and missing objects return the same 404 response. All three
owners retain access, and admin receives no special access.

### F-002 — Reports lack tenant authorization (medium)

**Expected:** only members of a report's tenant may read it. **Observed:** Alice
retrieved the south report, and Carol retrieved the north report. Preconditions:
any valid identity and an existing report ID.

**Trace:** middleware authenticated the user, but report() checked only existence
and returned the report without consulting identity. **Reproduction:** as Alice,
GET /reports/report-s returned 200 with a south tenant field; /reports/report-n
was the legitimate control. The four-identity/two-report matrix demonstrated four
cross-tenant successes. Impact is cross-tenant report disclosure; no write path exists.

**Fix applied and verified:** report() receives Request and checks the report's
tenant against the authenticated identity before returning data. Cross-tenant
and missing reports return 404. Same-tenant members and admin retain read access.

### F-003 — Client price controls order total (high)

**Expected:** every book costs 1,000 cents and total equals quantity times catalog
price. **Observed:** a quantity-one book with unit_price_cents=1 produced a 201
order totaling one cent. Preconditions: a valid identity and known product SKU.

**Trace:** Purchase validated numeric bounds, purchase() checked SKU existence,
then multiplied quantity by the client-provided price and stored that total.
**Reproduction:** as Alice, POST /orders with
`{"sku":"book","quantity":1,"unit_price_cents":1}`. Actual total was 1 versus
expected 1000. The regression also tested quantity two (2 versus expected 2000)
and a legitimate catalog-price purchase. Impact demonstrated is an underpriced
stored order; actual monetary loss or fulfillment was not tested and no payment
integration exists.

**Fix applied and verified:** calculate totals from CATALOG[body.sku]. Keep the
documented request fields and their validation for compatibility. The same
one-cent request remains accepted but now totals 1,000 cents; quantity two totals
2,000. Normal purchases and owner-scoped order listings continue working.

## Evidence and reproducibility

- [Minimal reproduction](assessment/reproduce.py): run `python -m assessment.reproduce`
  from the workspace. [Before](assessment/before-proof.json) and
  [after](assessment/after-proof.json) record statuses, disclosure booleans, and
  totals without credentials or resource bodies.
- [Regression suite](assessment/test_security.py): run
  `python -m unittest discover -s assessment -p test_security.py -v`.
  [Before](assessment/before-tests.txt): five tests, nine failing subcases across
  the three findings. [After](assessment/after-tests.txt): all five tests pass.
  PowerShell's saved stderr wrapper says NativeCommandError because unittest
  writes progress to stderr; the before run genuinely failed, while the after
  output ends in OK. A separate clean run confirmed process exit code 0.
- [Assessment log](assessment/log.md) and [finding records](assessment/findings.json)
  preserve scope, expected behavior, evidence, and uncertainty.

Original app/app.py SHA-256:
`B6CC46582538A044A4D47604C70E586AF8602D0958DC66D35FED3609BEF685B0`.
Patched SHA-256:
`061D490B00B25D1414EAEA3FB52951A27BF964C7E10680A08525DFA7265F9625`.

## Checks and coverage gaps

Verified public root/health, missing and invalid credentials on all documented
private GET routes and OpenAPI, unauthenticated order rejection without state
change, all identities on /me, full invoice/report matrices, admin export for all
roles (including encoded slash), catalog pricing, order owner isolation, unknown
resources/SKUs, missing fields, quantity bounds, and invalid price rejection.
The middleware already protects administrative export; its handler's absence of
a redundant role check is not a finding. Order listing already filters by owner.

Source review found no SQL, templates, file operations, uploads, subprocesses,
outbound integration, or cookie session flow to exercise. Fixture tokens are
explicitly public test credentials; their predictability is not reported as a
production authentication vulnerability. Authentication accepts a recognized
token without the Bearer prefix too; this still requires the same credential
and no authorization bypass was demonstrated.

Installed versions: FastAPI 0.115.6, Starlette 0.41.3, Pydantic 2.13.4, HTTPX
0.26.0, Uvicorn 0.34.0. No advisory lookup occurred, so dependency vulnerability
status remains unknown. No scanner or optional seca helper was used.

Not assessed: real HTTP transport, proxy normalization, TLS, browser behavior,
deployment headers, concurrency/order-ID races, load/denial of service, exhaustive
input fuzzing, persistent storage, real session lifecycle, or external payment
behavior. No unresolved likely findings are asserted. The focused fixes preserve
the documented API, but these tests cannot establish behavior for every malformed
request or deployment configuration.
