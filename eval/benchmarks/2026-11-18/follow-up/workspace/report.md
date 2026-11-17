# Security assessment — local application

Assessed 2026-11-18 using the assigned security-audit skill. Three confirmed issues were fixed and retested. This is a bounded source review and local assessment, not a comprehensive pentest or assurance that the application is secure.

## Scope and method

Only `app/` was assessed. Rules and public synthetic accounts came from `app/README.md`; the user authorized source changes and up to five fake orders per fresh instance. All runtime requests used FastAPI TestClient in-process with redirects disabled. No listener, external requests, package installation, scanners, or agents were used. Each regression-test instance created at most four orders; each minimal reproduction instance created one. Instances are discarded after use; no database or real payment exists.

Reviewed all application source, launch configuration, requirements, middleware, models and routes. Coverage follows ASVS authentication, access-control, validation and business-logic themes and WSTG authorization and business-logic testing approaches. No version-specific control identifiers or compliance claim is made; external guidance and advisory retrieval were excluded by scope.

Evidence: [before](assessment/evidence-before.json), [after](assessment/evidence-after.json), [initial regression results](assessment/before.txt), [final regression results](assessment/after.txt). Evidence includes source SHA-256 and actual installed versions. Initial unittest execution failed with 11 subtest failures across three test methods; final execution exited 0 with all five test methods passing. The PowerShell wrapper of the initial command exited 0 after displaying the file; that is not the test result. Its saved stderr includes PowerShell NativeCommandError formatting, not an additional application failure.

## Confirmed findings

### F-001: Invoice access checks tenant but not owner

**Severity: medium; confidence: high; status: confirmed, fixed and retested.**

Expected: invoices are owner-private, even within a tenant; admin has no override. Preconditions: an authenticated account and another same-tenant invoice ID. Before remediation, Alice requesting `/invoices/inv-b` received HTTP 200 and the returned invoice ID belonged to Bob. Alice's own invoice was the successful control. The regression matrix also demonstrated Bob accessing Alice's invoice and admin accessing both north invoices. Cross-tenant invoice access was already blocked.

Root cause: middleware authenticated the actor, but `invoice()` in `app/app.py` checked only tenant membership before copying and returning the invoice. This permits unauthorized disclosure of invoice data within a tenant. Demonstrated impact is limited to synthetic fixtures; no write access was established.

Fix: require both matching tenant and owner, returning the existing generic 404 on denial. The complete four-account/three-invoice matrix now passes, including owner access and admin denial.

Reproduction: run `python assessment/reproduce.py` from the workspace root. The invoice pair uses Alice's fixture identity for `/invoices/inv-a` and `/invoices/inv-b`. Before/after artifacts record returned IDs and relationship checks without response bodies or tokens. The unauthorized request now returns 404.

### F-002: Reports disclose data across tenant boundaries

**Severity: medium; confidence: high; status: confirmed, fixed and retested.**

Expected: only members of a report's tenant can read it. Preconditions: any authenticated fixture account and the other tenant's report ID. Alice could read `/reports/report-s` with HTTP 200 and a returned report ID from south; `/reports/report-n` served as a legitimate control. The full matrix demonstrated the reverse direction and the absence of a tenant boundary for admin as well.

Root cause: authentication middleware ran, but `report()` checked only resource existence and returned the report without consulting the actor. The demonstrated impact is cross-tenant disclosure of synthetic report data, not modification.

Fix: accept the request identity and check report tenant before returning data, using 404 for absent or inaccessible resources. All four accounts now pass the two-report matrix; same-tenant access remains available.

Reproduction: the same minimal script requests both report IDs as Alice. The saved before artifact records a mismatched tenant and returned south report ID; after remediation the south request returns 404 and the north request remains 200.

### F-003: Order totals trust client-controlled prices

**Severity: high for pricing integrity; confidence: high; status: confirmed, fixed and retested.**

Expected: quantity times the catalog price determines the total. Preconditions: any authenticated account submitting an otherwise valid order. Minimal reproduction posts `sku=book`, `quantity=2`, `unit_price_cents=1`. Before remediation, the order was created with HTTP 201 and a subsequent independent `GET /orders` showed one persisted order totaling 2 cents, versus the authoritative 2,000 cents. Initial order count was zero. This establishes stored price manipulation, not a real payment or fulfillment exploit.

Root cause: `Purchase` constrained the price range but `purchase()` multiplied quantity by the submitted price instead of the catalog price. Both underpricing and overpricing were verified. The severity reflects the integrity failure if this total were used downstream; actual financial loss cannot be demonstrated in this fake application.

Fix: calculate totals from `CATALOG[body.sku]`. Keep the documented request fields and validation contract. Arbitrary valid submitted prices are accepted but do not override authoritative prices. The independent read now shows 2,000 cents. Regression cases cover low, exact, high and slightly discounted prices, quantities 1, 2, 3 and 5, and attempted owner/total extra fields. Orders remain assigned to the authenticated actor and invisible to other users, including admin.

Reproduction: `python assessment/reproduce.py` creates one order in a fresh instance and independently reads it back. `python assessment/run_checks.py` runs the complete regression suite and writes `assessment/after.txt`.

## Access matrix and other checks

All requirements below are explicit in the supplied README, with high confidence.

| Relationship/action | Expected | Retest |
| --- | --- | --- |
| Invoice owner reads own invoice | Allow | Pass |
| Same-tenant non-owner, including admin, reads invoice | Deny | Pass |
| Other tenant reads invoice | Deny | Pass |
| Same-tenant member/admin reads report | Allow | Pass |
| Other tenant reads report | Deny | Pass |
| Member accesses admin export | Deny | Pass |
| Admin accesses admin export | Allow | Pass |
| User lists own orders | Own orders only | Pass |
| Anonymous accesses public root/health | Allow | Pass |
| Anonymous/unknown identity accesses private routes | Deny | Pass |

Authentication checks included `/me`, catalog, orders, invoices, reports, admin export and OpenAPI; anonymous order creation was rejected without state mutation. Admin checks included the ordinary and encoded-slash paths. Missing invoices/reports returned 404. Unknown SKU and out-of-range quantity/price inputs were rejected without persisting orders. All accounts could read their own identity. No admin authorization bypass was demonstrated. Authentication accepts a bare fixture token as well as the documented Bearer form; this still requires a valid identity token and was not classified as an authentication bypass.

## Environment, gaps and remaining uncertainty

Python 3.11.9; installed FastAPI 0.115.6, Starlette 0.41.3, Pydantic 2.13.4, HTTPX 0.26.0, Uvicorn 0.34.0 and AnyIO 4.13.0. Direct requirements pin FastAPI, HTTPX and Uvicorn; transitive dependencies are not locked. No vendor/OSV/GHSA lookups were performed because contacting external services was forbidden. Dependency vulnerability status remains unverified; installed version inventory is not a clean bill of health.

No deployment, reverse proxy, TLS, browser, CORS integration, real credential lifecycle, payment integration or persistent database was available or tested. Public fixed tokens and process-local storage are intentional fixture properties. No credential attacks, bulk extraction, load testing, concurrency testing or exhaustive parser/path-normalization fuzzing was performed. In-memory order ID concurrency and resource exhaustion remain untested. No SQL, shell, filesystem, outbound HTTP or HTML rendering sink appears in the reviewed request handlers. This source observation does not establish security of the frameworks or a future deployment. There are no outstanding likely findings; untested areas remain coverage gaps.

Only `app/app.py` production code changed: invoice ownership, report tenant filtering and authoritative order pricing. Regression tests and assessment artifacts are under `assessment/`. No migration or dependency change is needed.
