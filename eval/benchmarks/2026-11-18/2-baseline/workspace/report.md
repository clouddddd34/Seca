# Local application security assessment

Date: 2026-11-18

## Scope and method

Assessed only the fake-data application in `app/`, following `app/README.md`. Read all application source, runner configuration, and dependency declarations. Used installed Python packages and FastAPI TestClient; no listener, external services, package installation, skills, delegation, or scans of other software. No seca executable was needed. All scripts remain in this workspace.

Three confirmed security defects were fixed in `app/app.py`. Severity below describes the violated application boundary, not real-world financial or data loss: this fixture contains only synthetic data.

## Findings, evidence, and fixes

All reproduction requests below use `Authorization: Bearer fixture-alice`. Run `python reproduce.py` from the workspace to exercise the same requests against the current source. Original responses were observed before editing the application.

### 1. Private invoice disclosure to other tenant members (medium; CWE-639)

`GET /invoices/inv-b` originally returned HTTP 200 with:

```json
{"id":"inv-b","owner":"bob","tenant":"north","amount":200}
```

The handler checked tenant membership instead of ownership. Alice could read Bob's invoice, and the north admin could read invoices despite having no special invoice privilege. An authenticated user who knows an invoice ID could access another owner's private information within the tenant.

Fix: compare the invoice owner with the authenticated user's ID. Unauthorized and nonexistent invoices both return HTTP 404 with `{"detail":"Not found"}`. The reproduction now returns that response. Regression coverage checks every combination of four users and three invoices, including denied admin access and successful owner access.

### 2. Cross-tenant report disclosure (medium; CWE-862)

`GET /reports/report-s` originally returned HTTP 200 with:

```json
{"id":"report-s","tenant":"south","summary":"Synthetic south report"}
```

The report handler authenticated through middleware but never authorized tenant membership. Any fixture account could read either tenant's report.

Fix: resolve the report and compare its tenant with the authenticated user's tenant. Unauthorized and missing reports return the same HTTP 404. The reproduction now returns 404. Regression coverage checks all four accounts against both reports, preserving same-tenant sharing and denying cross-tenant access, including for admin.

### 3. Client-controlled order price (high; CWE-602)

`POST /orders` with:

```json
{"sku":"book","quantity":2,"unit_price_cents":1}
```

originally returned HTTP 201 with:

```json
{"id":1,"owner":"alice","sku":"book","quantity":2,"total_cents":2}
```

The catalog price is 1000 cents per book, so the required total was 2000 cents. The handler multiplied quantity by the client's price, enabling an authenticated buyer to choose an arbitrarily low permitted charge.

Fix: compute the total using `CATALOG[body.sku]`. The existing request field and validation remain compatible, but supplied prices cannot affect the total. The same reproduction now returns HTTP 201 and `total_cents: 2000`. Regression coverage includes low, exact, and high supplied prices, quantities 1, 2, and 5, and per-user order isolation. High supplied prices also yield exactly the catalog total, as required by the README.

## Checks performed

- `python -m unittest -v test_security`: all six test methods passed.
- `python reproduce.py`: confirmed both disclosure attempts now return 404, the underpriced purchase totals 2000 cents, and tested admin paths deny Alice.
- Ran the regression suite against an in-memory reconstruction of the original vulnerable checks and calculation. Exactly the invoice, report, and pricing test methods detected failures (nine assertions/subtests in total); the other three methods passed. This did not alter the fixed source.
- Authentication: missing and invalid tokens denied on every defined protected endpoint and the generated OpenAPI schema; `/` and `/health` remained public. `/me` returned each fixture account's identity.
- Admin authorization: all three members denied and admin allowed on `/admin/export`, encoded slash, encoded initial character, and trailing-slash variants. The reproduction's double-slash URL returned 404; TestClient URL handling means this is not evidence about raw proxy normalization.
- Input validation: quantities 0 and 6, prices 0 and 100001, and missing required fields returned 422; unknown product returned 404. Invalid requests created no orders.
- Invoice/report missing IDs returned 404. Authorized resource contents and order ownership were checked.
- Every test method gets a fresh application instance. The pricing test created four orders; other passing test methods created none. Each reproduction run created one order in its own fresh instance. The in-memory pre-fix pricing test stopped after one order. No instance exceeded five orders.

## Coverage gaps and remaining uncertainty

This is a focused local assessment, not an exhaustive penetration test. TestClient exercises application middleware and routing but not a real HTTP server, TLS, reverse proxy, browser, or deployment configuration. No dependency vulnerability lookup or network audit was performed. No load, denial-of-service, concurrency, or exhaustive malformed-request fuzzing was attempted. The in-memory order ID allocation and storage were reviewed but not stress-tested for concurrent use or persistence.

Public fixture tokens are intentionally documented and are not reported as leaked secrets. Token lifecycle, production credential strength, and account provisioning cannot be assessed from these fixtures. The existing parser also accepts a bare known fixture token without the `Bearer ` prefix; this still requires a valid credential and was not treated as an authentication bypass or changed in these focused fixes.

No confirmed admin bypass or cross-user order-list disclosure was found in the exercised cases; this does not prove absence for all deployment environments or inputs. There is no database, payment integration, file operation, email service, or application HTML rendering in the inspected implementation, so corresponding integration attack surfaces were not exercised. The app remains a local training fixture, not a production-ready service.
