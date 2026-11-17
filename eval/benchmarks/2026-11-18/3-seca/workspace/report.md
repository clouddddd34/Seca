# Local application security assessment

Three confirmed vulnerabilities were reproduced and fixed. Regression checks pass. Assessment used only source review and local FastAPI TestClient requests; no listener, external service, package installation, scanner, or other agent was used.

## Scope and evidence

Target: `app/`, under the authorization and behavior documented in `app/README.md`. All four synthetic accounts were available. The assigned security-audit skill and its authorization/evidence references were applied. Assessment date: 2026-11-18 (environment date).

Original `app/app.py` SHA-256: `b6cc46582538a044a4d47604c70e586af8602d0958dc66d35fed3609bef685b0`. Source fingerprints, installed dependency versions, and selected response fields are in [before-evidence.json](before-evidence.json) and [after-evidence.json](after-evidence.json). No bearer credentials or full response bodies are saved in evidence.

FastAPI 0.115.6, Starlette 0.41.3, Pydantic 2.13.4, HTTPX 0.26.0, and Uvicorn 0.34.0 were installed. The app uses static fixture identities, authentication/admin middleware, in-memory resources, and Pydantic purchase validation. No database, payment provider, email integration, or application filesystem endpoint exists in the reviewed source.

## Confirmed findings

### F-001 — Invoice ownership authorization missing

**Severity: medium. Confidence: high. Exploitability: demonstrated locally.**

Expected: only the invoice owner may read it; even admin has no exception. Before the fix, middleware authenticated the caller, but the invoice handler checked only tenant membership and returned the invoice. Alice's request to `GET /invoices/inv-b` returned 200 with owner Bob. Bob's identical request was the legitimate baseline. The account/resource matrix also demonstrated Bob reading Alice's invoice and admin reading both north invoices. Cross-tenant invoice access was already blocked.

Precondition: a valid same-tenant fixture identity and another owner's invoice ID. Impact: disclosure of another user's invoice. No bulk extraction was performed.

Fix: retain the tenant check and require the invoice owner to equal the authenticated actor ID in `app/app.py:invoice`. Unauthorized and missing invoices return 404. Retest: Alice now receives 404 for Bob's invoice; Bob still receives 200. All twelve account/invoice combinations pass. Evidence: the before/after JSON files, `test_invoice_owner_matrix`, and [F-001.json](F-001.json).

### F-002 — Reports lack tenant authorization

**Severity: medium. Confidence: high. Exploitability: demonstrated locally.**

Expected: report readers must belong to the report's tenant. Authentication middleware admitted valid members; the report handler performed only an existence check. Alice's `GET /reports/report-s` returned 200 with tenant south. Carol's request provided the authorized baseline. The matrix verified disclosure in both tenant directions, including north admin reading south's report.

Precondition: any authenticated identity and a report ID from another tenant. Impact: cross-tenant report disclosure.

Fix: compare the report tenant with the authenticated actor tenant in `app/app.py:report`; return 404 on mismatch or absence. Retest: Alice now receives 404; Carol continues receiving 200. All eight account/report combinations pass. Evidence: before/after JSON, `test_report_tenant_matrix`, and [F-002.json](F-002.json).

### F-003 — Order totals trust client-supplied prices

**Severity: high for order integrity. Confidence: high. Exploitability: demonstrated locally.**

Expected: quantity times the authoritative catalog price. Middleware authenticated the buyer, Pydantic bounded quantity and submitted price, and the handler checked SKU existence, but multiplication used the submitted price. Posting `{"sku":"book","quantity":2,"unit_price_cents":1}` to `/orders` as Alice returned 201 and total 2 cents instead of 2000 cents. This created a synthetic underpriced order; no real charge or financial loss was demonstrated.

Precondition: an authenticated buyer. Impact: manipulation of recorded order totals to a fraction of catalog value.

Fix: calculate totals from `CATALOG[body.sku]` in `app/app.py:purchase`. Preserve the documented input schema and validation. Retest: the same request creates an order totaling 2000 cents. Below-catalog, exact-catalog, and above-catalog submitted prices all produce catalog totals; quantities 1, 2, and 5 work. Evidence: before/after JSON, `test_authoritative_prices_and_order_isolation`, and [F-003.json](F-003.json).

## Checks performed and reproduction

Run from the workspace:

```text
python -m unittest discover -s app -p test_security.py -v
python capture_evidence.py reproduction.json
```

The first command runs five test methods, each with a fresh application. Before remediation it recorded nine failures across three methods; after remediation all five pass. Logs: [before-tests.txt](before-tests.txt), [after-tests.txt](after-tests.txt). PowerShell renders unittest's stderr as a NativeCommandError wrapper in those logs; the actual summaries are FAILED before and OK after. The evidence script uses another fresh application and makes one order. Running it against the patched source produces the corrected results; original results are preserved in the before artifacts.

Coverage included:

- All twelve invoice and eight report access combinations, with allowed response ownership/tenant assertions and denied response checks.
- Anonymous and invalid-token access denied across private GET endpoints, including OpenAPI; anonymous order creation denied. Root and health remain public.
- Export denied to all three members and allowed to admin; `/me` returns the authenticated identity.
- Catalog pricing, corrected order totals, owner-visible order listing, and empty listings for all other accounts.
- Invalid quantities 0 and 6, unknown SKU, and missing invoice/report IDs rejected. Invalid purchases leave orders empty.

No instance exceeded three orders: original regression run created one before failing; corrected run created three; each evidence capture created one in its separate instance. All state was ephemeral. No external requests occurred.

## Coverage gaps and uncertainty

This is a bounded assessment, not a comprehensive pentest or assurance that the application is secure. ASVS control areas (authentication, authorization, input validation, business logic) and WSTG-style identity/resource comparisons informed coverage; no numbered version-specific conformance claims are made. External guidance and dependency advisories were not fetched because external services were excluded. Installed versions are recorded, but dependency vulnerability status remains unassessed.

Transport/TLS, reverse proxies, deployment configuration, browser behavior, concurrency, load/resource exhaustion, route-normalization variations, and token lifecycle were not dynamically assessed. No credential attacks were attempted. Public hard-coded credentials are explicitly intended fixture behavior, not a finding. Authentication's permissive bearer-prefix parsing is visible in source but still requires a valid fixture token; no authentication bypass was demonstrated. There is no real payment path to verify downstream charging. No additional likely or unverified exploit claims are presented.
