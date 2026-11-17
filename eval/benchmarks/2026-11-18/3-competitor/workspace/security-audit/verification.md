# Sequential refutation, before fixes
Re-read app/app.py entrypoints and controls from numbered source after hunting, without consulting hunting notes. No separate agent used, per user instruction.

- Invoice: confirmed. Middleware authenticates, and line 65 enforces tenant membership, the strongest control. Alice and Bob share north, so this control permits Bob's private invoice to Alice and permits admin access, contrary to README. Return at 67 exposes amount and owner. Cross-tenant 404 limits but does not refute owner disclosure.
- Reports: confirmed. Middleware authenticates; line 71 checks only existence. No tenant control occurs before return at 73. Both directions reproduced. Synthetic summary only; no claim of real confidential records.
- Pricing: confirmed. Purchase fields enforce positive integers and quantity 1-5, and SKU lookup is enforced at 81. Price 1 is nevertheless valid; multiplication at 85 trusts it, and append at 86 persists total 2 instead of 2000. No real charge occurs; impact is fake order integrity.
- Admin bypass: rejected for the direct/encoded route paths tested. Prefix role guard at 46-47 precedes dispatch; encoded letters/slash are decoded before the guard. TestClient's //admin/export is interpreted as a URL authority and is not proof about raw ASGI double-slash paths. Add raw-path coverage to regression suite.

Severity: Medium each, high confidence with local reproduction. Each defeats its specified control, but this authorized target contains only synthetic data and no actual payments; no real financial loss or production compromise claimed.
