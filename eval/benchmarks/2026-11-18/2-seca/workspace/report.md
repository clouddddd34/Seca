# Local application security assessment

Assessed on 2026-11-18. Three confirmed security bugs were reproduced locally, fixed in `app/app.py`, and retested successfully. Severity below reflects the application's intended security boundaries; all demonstrated data and orders were synthetic. This is a bounded assessment, not a comprehensive pentest or assurance that the application is secure.

## Scope and method

Applied `assigned-skill/SKILL.md` and its access-rules, evidence, and helper guidance. Requirements came from `app/README.md`. Reviewed all application source, runner, and requirements. Used installed Python packages and FastAPI TestClient only: no listener, external requests, package installation, scanners, or delegation. Each test uses a fresh instance; no instance received more than three orders. Each standalone reproduction creates one order.

Mapped HTTP middleware authentication, admin path enforcement, object authorization, Pydantic validation, catalog-to-order pricing, and in-memory order storage. The trust boundaries are unauthenticated requests, authenticated identities, owner/tenant/role restrictions, and client-controlled purchase fields. Review covered authentication, access control, validation, and business logic categories associated with OWASP ASVS/WSTG; no version-specific control compliance is claimed. External guidance and advisory lookups were excluded by the no-external-services scope.

| Actor/resource relationship | Required behavior |
| --- | --- |
| Anonymous | Only `/` and `/health` public |
| Invoice owner | May read own invoice |
| Other user, including same-tenant admin | Cannot read invoice |
| Same-tenant member or admin | May read tenant report |
| Different tenant | Cannot read report |
| Admin / member | Export allowed / forbidden |
| Order creator / other user | Own orders visible / others' orders hidden |
| Purchase client | Quantity 1–5; total uses catalog price |

All rules above are explicitly documented, not inferred privileges.

## Confirmed findings

### F-001 — Same-tenant invoice disclosure (medium severity; high confidence)

**Expected:** An invoice is readable only by its owner; admins have no exception. **Observed:** Alice's `GET /invoices/inv-b` returned HTTP 200 and the synthetic owner `bob`. Alice's own invoice also returned 200 as a legitimate control. The original matrix additionally demonstrated Bob accessing Alice's invoice and admin accessing both north invoices.

**Precondition and cause:** Any authenticated user sharing the invoice tenant can supply its ID. Authentication middleware establishes identity, but the invoice handler originally checked only tenant equality before returning the complete invoice. This discloses private invoice information within a tenant; cross-tenant invoice access was already denied.

**Fix:** Require both matching tenant and matching owner before returning the invoice; return the same 404 as for a missing invoice on denial. The regression matrix covers all four accounts against all three invoices, including admin denial and every owner's successful read.

### F-002 — Cross-tenant report disclosure (medium severity; high confidence)

**Expected:** Reports are restricted to members of their tenant. **Observed:** Alice's `GET /reports/report-s` returned HTTP 200 and tenant `south`; her own north report also returned 200. Matrix tests demonstrated the reciprocal south-to-north failure and cross-tenant admin access.

**Precondition and cause:** Any authenticated account knowing a report ID can read it. Middleware authenticates this route but imposes no tenant boundary; the original handler only checked that the ID existed. This exposes another tenant's report contents.

**Fix:** Pass the authenticated request to the report handler, retrieve the report, and enforce tenant equality before returning it. The matrix verifies both reports with all four accounts; missing and inaccessible reports return 404, and same-tenant reads still succeed.

### F-003 — Client-controlled order totals (high severity; high confidence)

**Expected:** Book price is 1,000 cents, and every order total is quantity times catalog price. **Observed:** Alice submitted `{"sku":"book","quantity":2,"unit_price_cents":1}` to `POST /orders`. The response was 201 with `total_cents: 2`, rather than 2,000. The ordinary 1,000-cent input worked; a 2,000-cent input also incorrectly raised the price above the catalog value.

**Precondition and cause:** Any authenticated purchaser can supply a valid but false price. Pydantic limits the numeric range but does not establish price authority. The handler multiplied quantity by the supplied price and persisted that total. This demonstrates order-integrity failure and a 99.9% underpriced synthetic order, not an actual payment or financial loss.

**Fix:** Calculate totals from `CATALOG[body.sku]`. Preserve the documented request shape and existing validation, while ignoring the supplied price for calculation. Tests verify below-catalog, exact-catalog, and above-catalog values, quantity boundaries, and owner-specific order retrieval.

## Evidence and reproducibility

- `baseline-evidence.json` contains minimal selected response fields, the original source SHA-256, Python version, and resolved package versions. It confirms returned object ownership/tenancy, not just status codes. `fixed-evidence.json` records the same bounded requests after the fix, with unauthorized reads returning 404 and the purchase total returning 2,000.
- `reproduce.py` implements those requests. Run `python reproduce.py` from the workspace; it uses fixture identities internally without logging credentials. On the current fixed source it demonstrates corrected behavior. The original source hash identifies the assessed baseline; the vulnerable source was not retained as another runnable application.
- `test_security.py` is the regression suite. Run `python -m unittest -v test_security`. Before remediation, six test methods ran with ten failed subtests across the three findings (`baseline-tests.txt`). After remediation, all six methods passed, exit code 0 (`fixed-tests.txt`). The baseline PowerShell capture includes stderr wrapper noise; its unittest summary explicitly records failure, despite the encompassing shell command returning 0 after its subsequent package-version command.
- `audit.json` preserves finding records based on the skill's JSON template, checked coverage, and remaining gaps. No raw authorization headers or complete response bodies were saved in evidence.

## Other checks and limits

Authentication checks rejected absent and invalid tokens for `/me`, catalog, orders, invoices, reports, admin export, and OpenAPI; unauthorized order submission left storage empty. Both public endpoints remained available. All account identities resolved correctly. The export route allowed admin and denied all members; tested trailing-slash and encoded-path variants also denied members. These checks found no demonstrated admin bypass.

Missing objects and unknown SKUs returned 404. Invalid quantity and price ranges returned 422 without creating orders. Order listings remained owner-specific, including empty listings for other tenants and admin. Legitimate invoice/report/catalog/order behavior passed after the changes.

Installed versions: Python 3.11.9; FastAPI 0.115.6, Starlette 0.41.3, Pydantic 2.13.4, Uvicorn 0.34.0, HTTPX 0.26.0, AnyIO 4.13.0. Requirements pin the three direct packages; transitive packages are not locked. No current vulnerability advisory lookup was performed because external services were out of scope, so dependency vulnerability status remains unknown. Version inventory alone is not a vulnerability finding.

No production environment, real payment flow, browser frontend, TLS/proxy behavior, persistence, token issuance/revocation/expiry, concurrency, resource-exhaustion, or load testing was assessed. Public fixture tokens and in-memory storage are explicit training design choices, not newly reported security bugs. Authentication accepts a known token without the `Bearer ` prefix by source inspection; this still requires a valid token and was not classified as an authentication bypass. The optional seca helper was not needed; no scanner or helper-based assurance is claimed. There are no remaining unverified application findings from this bounded review, but the coverage gaps above remain.
