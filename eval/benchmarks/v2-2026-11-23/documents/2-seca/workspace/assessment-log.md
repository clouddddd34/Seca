# Assessment log

Scope: app/app.py and README; local FastAPI/HTTPX TestClient only. No external access, installations, delegation or other skills. Each test uses fresh synthetic state with at most ten shares and ten state changes.

Rules: README is the supplied authority. Read requires current document tenant plus ownership or an unrevoked, unexpired share. Only current same-tenant owners can grant/revoke; recipients must currently belong to the tenant. Inventory requires admin role and current tenant filtering.

Source reviewed: all four application endpoints, actor, document lookup, can_read and share validation. Candidates: read authorization omits tenant membership and share expiry. Existing owner, recipient, revocation and inventory checks require control tests. Bare identity parsing and in-memory credentials are assessed as fixture authentication, not production findings.

Next: run bounded regression tests before changes, retain failures, patch demonstrated read failures and rerun all checks.

Completed: two confirmed findings (F-001 tenant membership; F-002 expiry), focused can_read fix applied. Eight tests executed before (three failures) and after (all pass); separate probes confirmed full-document exposure before and denial after. State-changing controls inspected persisted state. Report and structured records written. No outstanding candidate remains from reviewed paths; deployment, advisories, concurrency and broad malformed-input coverage remain excluded/untested. Maximum per-instance activity: one share, three state changes.
