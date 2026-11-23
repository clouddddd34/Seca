from pathlib import Path
import json
p=Path('security-audit')
findings=[]
for key,title,line,testline,description,counter,condition,fix in [
 ('expired-share','Expired shares continue to disclose documents',45,23,
  'Bob requests document a after an owner-created share expires. The original read predicate checked recipient and revocation but ignored expires_at; the GET still returned 200 with the document.',
  'Share creation rejects past deadlines and read checks revoked. Neither re-evaluates a previously valid deadline at read time. The expiry and exact-deadline tests both returned 200 before the fix.',
  'A recipient has a previously valid, unrevoked share whose deadline has passed.',
  'Require time() < expires_at for each matching, unrevoked share; equality denies access.'),
 ('tenant-membership','Former tenant members retain document access',40,35,
  'After trusted directory migration from north to south, Bob can still read north document a through a live share; migrated owner Alice can also still read a. Both GETs returned 200. Current tenant membership was absent from can_read.',
  'Sharing and revocation check owner and current tenant; those guards do not execute on GET. Ownership and a live share cannot substitute for the separate current membership requirement. Both migration tests failed before the fix.',
  'The trusted directory moves a document owner or an existing share recipient to another tenant. The caller remains authenticated.',
  'Deny tenant mismatch before either ownership or share authorization.')]:
 f=dict(fingerprint='owasp-audit/access/app/app.py/'+key,verdict='confirmed',skill='owasp-audit',title=title,cwe='CWE-863',owasp_category='A01:2025',location={'file':'app/app.py','line':line},
 trace=[{'kind':'entrypoint','file':'app/app.py','line':48,'description':'Authenticated caller selects document ID in GET /documents/{doc_id}.'},{'kind':'propagation','file':'app/app.py','line':line,'description':'Original can_read omitted the required condition; cited current location contains its fix.'},{'kind':'sink','file':'app/app.py','line':54,'description':'Return the full copied document as JSON.'}],
 evidence=[{'file':'security-audit/original-app.py.txt','line':39,'description':'Preserved original read predicate.'},{'file':'security-audit/before-tests.txt','line':1,'description':'Four failing denial assertions observed HTTP 200 rather than 404.'},{'file':'app/test_security.py','line':testline,'description':'Executable regression test.'},{'file':'security-audit/after-tests.txt','line':1,'description':'All ten tests passed after the focused patch; Python exit code 0.'}],
 counterevidence=counter,confidence='high',reproduced=True,severity={'likelihood':{'score':'medium','reason':'Requires prior legitimate access followed by expiry or trusted migration.'},'impact':{'score':'medium','reason':'Read disclosure of previously accessible documents beyond authorization lifetime; no new grant, write, or broad arbitrary-document access demonstrated.'},'overall':'medium'},conditions=[{'kind':'authentication_level','description':'Authenticated fixture account.'},{'kind':'data_state','description':condition}],disposition='Fixed',ext={'description':description,'fix':fix,'regression_test':'app/test_security.py','fix_verified_on':'2026-11-23'})
 findings.append(f)
findings.sort(key=lambda x:x['fingerprint']); (p/'findings.json').write_text(json.dumps(findings,indent=2))
units=json.loads((p/'coverage.json').read_text())
results=[
 ('Current membership AND ownership or live share govern every document read.','Four original failures; tenant and expiry checks fixed; all read-policy tests pass.'),
 ('Only a current-tenant owner can grant to a current same-tenant recipient with a future deadline.','Owner/live grant succeeds; recipient reshare, cross-tenant/unknown recipient and past expiry fail; migrated owner cannot share. app/app.py:61-67.'),
 ('Only current-tenant owners revoke; revocation denies recipient reads.','Owner DELETE returns 204; Bob/Carol and migrated owner denied; revoked share no longer permits reads. app/app.py:73-79.'),
 ('Inventory requires admin role and filters by current tenant.','Bob denied; admin sees a,b in north and c after migration to south. app/app.py:84-86.'),
 ('Framework metadata must not expose document state.','Four default metadata routes return schema/static documentation, not document records; route list matches four business routes. security-audit/surface-checks.json.')]
for i,(u,(inv,result)) in enumerate(zip(units,results)):
 u.update(status='candidate' if i==0 else 'covered',reviewed_paths=['app/app.py','app/README.md','app/test_security.py'],checks=[dict(invariant=inv,method='Source trace and local TestClient requests',result=result)],finding_fingerprints=[f['fingerprint'] for f in findings] if i==0 else [])
def unit(name,category,status,invariant,result):
 return dict(id='app/app.py:'+name+':'+category[:3],surface=name,boundary='request to application state',owasp_category=category,status=status,reviewed_paths=['app/app.py','app/README.md'],checks=[dict(invariant=invariant,method='Complete source inspection; runtime checks where specified',result=result)],finding_fingerprints=[],unresolved=[])
units += [
 unit('all-business-routes','A07:2025','covered','Missing and unknown identities cannot use business routes.','actor runs before document/share lookup; valid-body requests without or with unknown credentials return 401. Fake identity mapping is explicitly a fixture.'),
 unit('share-input-and-path-parsing','A10:2025','covered','Malformed bodies and non-integer share IDs do not mutate state.','Two invalid share bodies and invalid DELETE ID return 422; zero shares created. No exception catch grants access.'),
 unit('response-and-configuration','A02:2025','covered','Review debug, CORS, error and metadata exposure.','No debug=True or permissive CORS configured; public schema/docs contain no application records. Deployment absent by fixture design.'),
 unit('runtime-sinks','A05:2025','not_applicable','Untrusted values must not reach executable SQL, shell or template sinks.','No such sinks; IDs use dictionary lookups and user data is serialized as JSON.'),
 unit('outbound-fetch','A01:2025','not_applicable','User input cannot induce server-side HTTP.','No outbound client, URL field or fetch call in app source.'),
 unit('state-transition-design','A06:2025','covered','Members cannot reshare or override owner and tenant fields.','Share model accepts recipient/expiry only; server sets document, id and revoked; owner/tenant checks precede append. No payment/job state machines.'),
 unit('state-integrity','A08:2025','covered','Client cannot inject serialized executable state or mutate returned objects by reference.','Pydantic parses JSON; server creates share records and deep-copies outputs; no pickle, dynamic imports or external effects.'),
 unit('audit-observability','A09:2025','covered','Check sensitive logs and security event recording.','No application logging or alerting calls; no sensitive logging sink. Observability recommendation recorded as hardening, without a traced exploit.'),
 unit('crypto','A04:2025','out_of_scope','Do not report fake tokens or memory storage as production weaknesses.','README explicitly defines synthetic tokens/storage; no production cryptography or transport configuration supplied.'),
 unit('dependency-and-deployment-assurance','A03:2025','out_of_scope','Do not claim a dependency or deployment audit without evidence.','No app lockfile, package manifest or deployment supplied; external advisory services and installs prohibited; no CVE assurance claimed.')]
(p/'coverage.json').write_text(json.dumps(units,indent=2))
(p/'hardening-notes.md').write_text('1. app/app.py:28,57,71: consider security-event logging for denied access and share/revocation events when adapting this fixture for deployment; no exploit attributed to absent logging.\n2. app/app.py:14-16: consider finite-number validation for expires_at; no cross-principal impact demonstrated from non-finite input, so no fix or vulnerability claimed.\n')
(p/'verification.md').write_text('''# Sequential verification and post-fix review
Delegation prohibited by user: verification used separate source re-derivation steps in the same context, not an independent agent.

Expired-share claim: re-read original app/app.py:39-52 and :55-64. Strongest controls are recipient match, revoked flag and future-at-creation validation. A valid share can later expire without revocation. There is no clock comparison on GET. Bob's a request returns the full document after expiry. Confirmed by two failing assertions (past and exact deadline).

Membership claim: independently re-read original read path and sharing/revocation guards. The user object is resolved afresh but unused by can_read; owner fast path and share path both skip tenant. Neither mutation guard applies to GET. README explicitly authorizes trusted migration and requires current membership separately from ownership/sharing. Confirmed by owner and recipient migration failures. Trusted setup is not itself the vulnerability.

Post-fix adversarial review: tenant guard precedes BOTH authorization alternatives; strict expiry predicate rejects equality; revoked still rejects; any live matching share suffices even alongside expired grants. No new exemption, route or mutation introduced. Current-tenant owner bypass of expiry is intentional ownership access. Mutations and inventory unchanged. All ten tests pass. No claim of independent-model review.

Coverage critic: enumerated eight routes (four business plus four metadata) in surface-checks.json and matched them to ledger. Inspected all 85 original source lines and both mutation siblings. No hidden jobs, upload handlers, persistence or network sinks. Added metadata and parser units; no remaining unmapped route. Out-of-scope cryptographic/dependency/deployment assurance justified by README and user restrictions. Candidate unit remains candidate after fixes. No candidate lacks a verdict.

Fixture exclusions: fake credentials/auth mapping, memory-only state, absent deployment are excluded conditions, not production findings. No other test/generated/vendor/doc candidate was promoted. Scope counts represent conditions, not vulnerabilities.
''')
print('Wrote 2 findings and',len(units),'coverage units')
