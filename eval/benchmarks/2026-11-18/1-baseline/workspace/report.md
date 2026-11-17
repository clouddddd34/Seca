# Local application security assessment

Assessed `app/` against `app/README.md` on 2026-11-18. Three meaningful security defects were reproduced and fixed. Severity below describes the violated application rule; this fixture contains synthetic data and has no real payment integration.

## Scope and method

Read all application source, runner, requirements, and intended rules. Used installed Python packages and FastAPI TestClient exclusively for requests; no listener, external service, package installation, other-software scanning, skills, or delegated agents were used. All artifacts are inside this workspace.

Each unittest creates and closes a fresh application instance. Price and ownership tests create three orders each on separate instances; the reproduction script creates one on its own instance. No instance creates more than three orders, below the authorized five-order limit.

## Findings, evidence, and fixes

All examples below use `Authorization: Bearer fixture-alice`. Raw before/after responses are recorded in `baseline-evidence.json` and `fixed-evidence.json`. Run `python -m app.reproduce` from the workspace root to exercise the three minimal cases against the current source.

### 1. Invoice authorization checks tenant but not owner — High (CWE-639)

`GET /invoices/inv-b` returned HTTP 200 and Bob's invoice, including `owner: bob` and `amount: 200`, to Alice. Both belong to north, but invoices must be private to their owners. The baseline authorization matrix also demonstrated Bob reading Alice's invoice and the north admin reading both members' invoices despite having no special invoice privilege.

The invoice handler now requires both tenant and owner to match the authenticated actor. Missing and unauthorized invoices return the same 404 response. The reproduction now returns `404 {"detail":"Not found"}`. Regression coverage checks all four actors against all three invoices, including successful owner access and denied admin access.

### 2. Reports lack tenant authorization — High (CWE-862)

`GET /reports/report-s` returned HTTP 200 and `{"id":"report-s","tenant":"south","summary":"Synthetic south report"}` to Alice in north. The handler previously checked only whether the report existed. Any authenticated account could read either tenant's report.

The report handler now receives the request identity and verifies the report's tenant before returning data. The reproduction now returns `404 {"detail":"Not found"}`. The regression matrix checks all four accounts against both reports; same-tenant sharing, including north admin access to north reports, remains permitted.

### 3. Client controls charged order price — High (CWE-602)

`POST /orders` with `{"sku":"book","quantity":1,"unit_price_cents":1}` returned HTTP 201 and an order with `total_cents: 1`, although the catalog requires 1000 cents. Model bounds allowed this price and did not establish its authority. A second regression case also demonstrated overcharging: quantity 2 and client price 100000 yielded 200000 rather than 2000 cents.

Order totals now use `quantity * CATALOG[sku]`. The request schema, existing price-field validation, quantity limits, unknown-product behavior, and response shape remain intact. The minimal request still succeeds with HTTP 201, but its total is now 1000 cents. Tests cover low, matching, and high client prices and valid quantity endpoints 1 and 5.

## Checks performed

Command: `python -m unittest app.test_security -v` from the workspace root.

- Before fixes: eight test methods ran, with ten failing subtests across the three vulnerable behaviors. Five methods passed. Output: `baseline-tests.txt`.
- After fixes: all eight test methods passed. Output: `fixed-tests.txt`.
- Verified public `/` and `/health`; missing/invalid authentication rejected on protected resources, including OpenAPI, and unauthenticated order creation rejected.
- Verified all three members denied admin export and admin permitted, including trailing-slash and percent-encoded path variants.
- Verified invoice ownership and report tenant matrices, missing resource handling, identity, and catalog output.
- Verified order lists remain scoped to their owner, and client `owner` and `total_cents` fields do not override server values.
- Verified quantity and price bounds and unknown SKU rejection without creating orders.
- Re-ran the one-order evidence script after fixes and confirmed corrected response bodies.

The captured test logs contain PowerShell's `NativeCommandError` formatting because unittest writes progress to stderr; the final unittest summary is authoritative (baseline `FAILED (failures=10)`, fixed `OK`).

## Coverage gaps and remaining uncertainty

This is a focused source review and deterministic local regression assessment, not an exhaustive proof of security. No deployed HTTP server, reverse proxy, TLS, browser behavior, load, concurrency, or dependency vulnerability audit was tested. TestClient path checks do not establish behavior through an arbitrary proxy. In-memory order ID allocation and persistence were not stress-tested.

Fixture tokens are deliberately public, static credentials per the README; production identity lifecycle and credential security are outside this fixture's intended behavior. The parser also accepts a raw known token without the Bearer prefix; this still requires a valid fixture token and was not treated as an authentication bypass or changed here. Input coercion and malformed-body combinations were not exhaustively fuzzed. There is no real payment processor to verify; the pricing evidence establishes the stored/returned order total only.

Future routes must preserve the existing authentication and admin boundary assumptions. No additional exploitable issue is claimed beyond the three verified findings above.
