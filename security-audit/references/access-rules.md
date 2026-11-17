# Access rules

Build a compact matrix for the relevant workflows. Request test accounts through the environment's normal credential mechanism; do not ask users to paste passwords into the matrix.

| Actor / role | Resource relationship | Action | Expected result | Rule source | Confidence |
| --- | --- | --- | --- | --- | --- |
| Member A | Own invoice | Read | Allow | Product requirement | Confirmed |
| Member A | Member B's invoice, same organization | Read | Unknown | Not documented | Needs clarification |
| Member A | Different organization's invoice | Read | Deny | Tenant isolation tests | Inferred |
| Anonymous | Private invoice | Read | Deny | Product requirement | Confirmed |

Check both horizontal boundaries (two users with the same role) and vertical boundaries (different privileges). Consider tenant membership, ownership transfers, expired invitations, and revoked roles when relevant.

For a request replay, establish a successful authorized baseline. Change only the identity or resource relationship under test, using test-owned resources. Ensure cookies, authorization headers, CSRF tokens, and client session state correspond to the intended account; mixed sessions invalidate the result. Do not follow a redirect outside scope. Avoid automatic retries of state-changing requests.

Compare actual data access or state transitions, not only HTTP status codes. A 200 response can contain an access-denied page; a denied response can still accompany an unintended state change. Observe only the minimum data required to establish the outcome.
