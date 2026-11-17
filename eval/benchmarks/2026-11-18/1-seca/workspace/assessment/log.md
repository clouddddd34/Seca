# Assessment log

Scope: app/ source and in-process FastAPI TestClient only. No external services,
package installation, scans of other software, or delegation. Maximum five fake
orders per fresh app; tests below create at most two. Evidence excludes credentials
and raw private responses. Requirements come from app/README.md.

Initial source review: Python FastAPI, static fixture bearer identities, middleware
authentication and admin prefix boundary, in-memory resources and orders. No
database, template rendering, uploads, subprocesses, outbound calls, or payment.

Access matrix: anonymous may read / and /health only; all four identities may
read /me and /catalog; invoices require exact owner (admin has no exception);
reports require matching tenant; export requires admin; order lists require owner.

Candidates: F-001 same-tenant invoice access; F-002 cross-tenant report access;
F-003 client-controlled totals. Pending local reproduction, fixes, and retest.

Dependency advisories will not be fetched because external contact is excluded.

Completed: all three candidates confirmed by minimal runtime proofs and failing
regression subcases. Source fixes applied to invoice owner check, report tenant
check, and catalog-based pricing. Retest: five tests pass; direct unittest process
exit 0. Before/after proofs and test output saved in assessment/. At most two
orders per instance throughout. Findings copied from the provided template into
findings.json; no raw credentials or private response bodies saved as evidence.

Covered: full identity/resource permission matrices, public/private authentication,
admin prefix including encoded slash, catalog price and quantities, owner-only
order lists, invalid inputs without writes, missing resources. No further candidate
findings pending. Remaining uncertainty: dependencies without current advisories,
transport/deployment, concurrency, exhaustive malformed inputs and load; report.md
details limitations. No external contact, scanner, or optional helper used.
