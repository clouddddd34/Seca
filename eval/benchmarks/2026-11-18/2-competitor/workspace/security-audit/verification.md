# Sequential refutation and post-fix review

User prohibits delegation; verification was a separate reread of numbered source,
after initial tests and before edits. No independent agent or model was used.
The app is deliberately a fixture, but is explicitly the runtime audit target:
its mounted handlers are included. Zero candidates excluded by location rules.

1. Invoice claim: original app/app.py:62-67, middleware :37-48. Strongest
   control is authenticated identity plus tenant equality. Neither compares owner.
   Alice reading inv-b returns Bob's owner and amount; Carol's inv-c is blocked.
   README explicitly forbids same-tenant access and admin exceptions. Confirmed.
2. Report claim: original :69-73, middleware :37-48. Authentication runs first,
   but the handler checks only existence; there is no report tenant predicate.
   Alice receives report-s. Same-tenant sharing is legitimate; cross-tenant
   sharing is not. Confirmed.
3. Price claim: original :27-30 and :79-87. Quantity and price bounds plus known
   SKU validation run before storage. The minimum price of 1 is nevertheless
   accepted and used rather than the catalog's 1000. Two books produce total 2.
   This crosses the merchant's pricing boundary, not merely self-impact.
   No actual payment or real money exists. Confirmed, limited to fake order data.
4. Admin bypass claim: :37-48 gates the decoded /admin prefix before routing.
   Members get 403 for canonical, trailing-slash and percent-encoded variants;
   admin gets 200. No bypass demonstrated. Rejected for tested local routing.

Post-fix adversarial review: invoice checks use server identity with no admin
exception; reports retain same-tenant sharing; missing and forbidden objects
both return identical 404 bodies. Authentication precedes either lookup. Order
total uses the known SKU catalog after validation; extra owner/total fields do
not override server values. Regression matrix covers every supplied account,
both tenants, minimum/maximum quantity, low/exact/high submitted prices, malformed
JSON and invalid values with no writes. No new routes or external sinks added.
Concurrency and large-payload stress are not proven by these checks; no race
finding is claimed from len()+append alone.
