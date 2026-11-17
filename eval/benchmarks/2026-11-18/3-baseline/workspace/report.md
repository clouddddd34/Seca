# Local application security assessment

## Scope and method

Assessed only `app/`, using its README as the authorization and behavior contract. Read all application source, launcher, and dependency declarations. Used installed Python packages and FastAPI TestClient, without a network listener, external requests, package installation, skills, other agents, or the optional seca executable. All assessment files are inside this workspace.

Each test method creates a fresh application. The purchase test creates four fake orders per instance; all other tests create none. Ran the suite once before fixes and once afterward (four orders in each of two separate instances). No real payment or other side effect exists in this fixture.

## Confirmed findings and fixes

Severity describes the potential effect in an application with real data; this fixture contains synthetic data and public test credentials.

### 1. Invoice ownership bypass — High, CWE-639 / CWE-863

The invoice handler checked tenant membership instead of ownership. Any north account, including the administrator, could read Alice's and Bob's private invoices. This violates the explicit rule that invoices are private even within a tenant and that administrators have no special invoice privilege.

Minimal reproduction before the fix: `GET /invoices/inv-b` with `Authorization: Bearer fixture-alice` returned HTTP 200 with Bob's invoice, rather than denying access. The regression suite also confirmed Bob reading Alice's invoice and Admin reading both north invoices. Cross-tenant invoice access was already denied.

Fix: compare the invoice owner to the authenticated actor's ID. Missing and unauthorized invoices both return 404. The regression matrix covers all four actors against all three invoices, legitimate owner reads, and a nonexistent invoice. All cases now pass.

### 2. Cross-tenant report disclosure — High, CWE-862

The report handler performed no tenant authorization after authentication. Any account could retrieve either tenant's report.

Minimal reproduction before the fix: `GET /reports/report-s` with `Authorization: Bearer fixture-alice` returned HTTP 200 instead of denying access. The suite reproduced north-to-south access for Alice, Bob, and Admin, and south-to-north access for Carol.

Fix: retrieve the authenticated actor and compare the report's tenant to the actor's tenant before returning data. Missing and unauthorized reports both return 404. Tests cover every actor/report combination, including legitimate same-tenant sharing and missing reports. All cases now pass.

### 3. Client-controlled order pricing — High, CWE-602

The purchase handler multiplied quantity by the submitted price rather than the catalog price. A buyer could reduce a book order from 1000 cents to 1 cent. This is an incorrect recorded order total; no actual payment processing exists here.

Minimal reproduction before the fix: `POST /orders` with Alice's bearer token and `{"sku":"book","quantity":1,"unit_price_cents":1}` returned HTTP 201 with `total_cents: 1`, instead of 1000. A separate test with quantity 2 and submitted price 100000 returned 200000 instead of 2000, confirming complete reliance on the submitted value.

Fix: calculate the total using `CATALOG[body.sku]`. Keep the existing request fields and validation for compatibility. Valid low and high submitted prices are accepted but do not determine the total. Tests cover low, matching, and high submitted prices; quantities 1, 2, and 5; and order-list isolation among all four actors. All cases now pass.

## Verification

Run from the workspace root:

```powershell
python -m unittest app.test_security -v
```

Before changes: five test methods ran, with ten failing subtests: four invoice authorization cases, four report authorization cases, and two pricing cases. Authentication/admin and invalid-purchase tests passed before changes.

After changes: all five test methods and their subtests passed. Regression tests are in `app/test_security.py`; focused production changes are confined to `app/app.py`.

Additional checks in that suite:

- `/` and `/health` remain public.
- Missing and invalid credentials receive 401 on `/me`, invoice/report reads, `/catalog`, `/orders`, `/admin/export`, and `/openapi.json`. An unauthenticated order submission also receives 401.
- All fixture accounts resolve to the expected identity.
- Only Admin can export, including the tested trailing-slash, percent-encoded `a`, and encoded slash variants of the admin path.
- Unknown products return 404; quantities 0, 6, and 1.5 and prices 0 and 100001 return 422, without creating orders.
- Catalog pricing remains 1000 cents for a book. Orders remain private to their creator, including against administrators.

## Coverage gaps and remaining uncertainty

This was a focused source review and deterministic in-process assessment, not an exhaustive proof of security. No deployment, reverse proxy, TLS, browser, live Uvicorn, load, concurrency, dependency-vulnerability, or external-service testing was performed. Encoded-path checks cover only the listed variants; production routing behavior could differ behind a proxy.

The fixture intentionally uses public static credentials and in-memory orders. Those are not treated as newly discovered production credential leaks. It has no database queries, template rendering, file operations, or outbound calls in its request handlers, so source review did not identify corresponding injection or SSRF sinks.

The existing authentication parser also accepts a raw valid fixture token without the `Bearer ` prefix (visible from `removeprefix` in the middleware). This still requires a recognized token and was not classified as an authentication bypass; strict authentication-scheme parsing was not changed or dynamically tested. Order IDs use list length and storage has no persistence or explicit concurrency controls; concurrent ordering and resource-exhaustion behavior remain untested. These limitations and the README's local-only warning remain relevant if the fixture is ever expanded beyond its authorized training use.
