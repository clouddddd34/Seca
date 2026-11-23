import json
from pathlib import Path
base=Path('security-audit')
findings=[]
for key,title,line,testline,description,counter,conditions in [
 ('share-expiry','Expired shares continue to disclose documents',43,27,'Bob can read Alice\'s document after the share expires. The original read predicate checks revocation but never expires_at.','The creation endpoint requires a future expiry and the read predicate rejects revoked shares. Neither enforces time at subsequent reads.',['Authenticated recipient with an unrevoked share whose expiry has passed']),
 ('tenant-membership','Migrated owners and recipients retain old-tenant document access',40,41,'After the trusted directory moves Alice or Bob to south, GET /documents/a still returns the north document. The original read policy ignores current tenant membership.','Sharing and revocation require current tenant membership; inventory filters by current tenant. Those sibling controls do not run on document reads.',['Existing owner or shared recipient','Trusted directory changes current membership; attacker does not control that operation'])]:
    findings.append(dict(fingerprint=f'owasp-audit/{key}/app/app.py/can_read',verdict='confirmed',skill='owasp-audit',title=title,cwe='CWE-863',owasp_category='A01:2025',location={'file':'security-audit/original-app.py.txt','line':line},trace=[{'kind':'entrypoint','file':'security-audit/original-app.py.txt','line':45,'description':'Authenticated GET /documents/{doc_id} accepts caller-controlled document ID'},{'kind':'propagation','file':'security-audit/original-app.py.txt','line':39,'description':description},{'kind':'sink','file':'security-audit/original-app.py.txt','line':51,'description':'Returns full document JSON across the access boundary'}],evidence=[{'file':'security-audit/responses.json','line':1,'description':'Original requests return 200 and Synthetic alpha; fixed requests return 404.'},{'file':'app/test_security.py','line':testline,'description':'Regression checks fail before the fix and pass after.'}],counterevidence=counter,confidence='high',reproduced=True,severity={'likelihood':{'score':'medium','reason':'Requires a previously granted relationship followed by expiry or membership change.'},'impact':{'score':'high','reason':'Fully defeats explicit document confidentiality control; returns entire protected document.'},'overall':'high'},conditions=[{'kind':'data_state','description':x} for x in conditions],disposition='Fixed',ext={'description':description,'remediation':'Read policy now requires current tenant membership before ownership/share checks, and an unrevoked share strictly before expires_at.','regression_test':'app/test_security.py','fix_verified_on':'2026-11-18'}))
findings.sort(key=lambda f:f['fingerprint'])
(base/'findings.json').write_text(json.dumps(findings,indent=2))
units=json.loads((base/'coverage.json').read_text())
routechecks={
'read':'Owner and live same-tenant recipient succeed; unshared member, other tenant, admin without share, missing document, expired share and migrated identities fail. Regression tests and responses.json demonstrate both fixed invariants.',
'share':'Owner plus current tenant checks precede append; cross-tenant and unknown recipients, past expiry and recipient resharing fail. tests share_validation, revocation_and_reshare, migrated_owner_cannot_mutate pass.',
'revoke':'Ownership and current tenant precede revoked=True. Recipient and migrated-owner revocation fail; owner revocation succeeds and blocks reads; fresh share restores access.',
'inventory':'Role guard rejects Bob. Current tenant filter returns a/b for north admin and c after directory migration to south; inventory test passes.',
'docs':'Local schema/docs routes return 200; schema describes routes and Share fields, not stored document bodies. No document-state sink on these routes.'}
for u in units:
    key=u['id'].split(':')[1]; n=int(u['owasp_category'][1:3])
    u['reviewed_paths']=['app/app.py','app/README.md']
    u['status']='covered'
    result=routechecks[key]
    invariant='Enforce the documented access boundary'
    if n==1 and key=='read':
        u['status']='candidate';u['finding_fingerprints']=[f['fingerprint'] for f in findings]
    elif n==3:
        u['status']='out_of_scope'; invariant='Dependency provenance and advisories';result='No manifest or lockfile supplied in app/. Registry access and packages forbidden; no dependency vulnerability claim.'
    elif n in [4,5,8]:
        u['status']='not_applicable';invariant={4:'No application cryptographic secret handling',5:'No interpreter or HTML input sink',8:'No untrusted code/deserialization or external side effects'}[n];result='Read full app/app.py: fixed fixture identities, typed JSON input, dictionary lookups and deep-copy JSON output only. No database, shell, filesystem, outbound HTTP, user HTML or unsafe deserializer.'
    elif n==7:
        invariant='Unknown or absent identity cannot access business routes';result='actor() rejects missing/unknown names with 401 on all four business routes (test_auth_and_unshared_reads). Synthetic token format, including permissive name parsing, is fixture authentication, not production assurance.' if key!='docs' else 'Documentation routes are intentionally anonymous and contain schema only.'
    elif n==2:
        invariant='Configuration does not expose stored state through debug/docs';result='FastAPI default debug=False; no CORS middleware or custom exception trace responses. Docs/schema requests were local only. Deployment absent and not assessed.'
    elif n==6:
        invariant='Workflow transitions preserve authorized sharing';result=routechecks[key]
    elif n==9:
        invariant='No credentials or document content sent to application logs';result='No application logging calls or external notification sink. Security event logging absent: hardening note, no demonstrated exploit.'
    elif n==10:
        invariant='Invalid identity/resource/authorization fails before protected sink';result='actor and document helpers raise HTTPException; mutation guards precede writes; rejected mutations leave shares unchanged. Nine regression tests pass; no catch-and-allow path.'
    u['checks']=[dict(invariant=invariant,method='Full source trace; local TestClient checks where cited',result=result)]
(base/'coverage.json').write_text(json.dumps(units,indent=2))
(base/'hardening-notes.md').write_text('Application security-event logging is absent (app/app.py); consider logging denials and share changes without credentials or document text. No traced logging-related vulnerability.\nMutation routes distinguish missing resources (404) from unauthorized existing resources (403). Identifiers and their sensitivity are not established as confidential in this synthetic fixture; no demonstrated sensitive metadata disclosure, and no behavioral change made.\n')
(base/'verification.md').write_text('Sequential refutation and post-fix review\n\nExpiry: independently re-read original-app.py.txt:39-51 and :54-65. Creation-time future validation and revocation filtering are strongest controls; neither checks elapsed time on read. Verdict: confirmed, supported by expired and exact-boundary failing tests.\n\nMembership: re-read original-app.py.txt:28-51, :58, :74, :83. Identity is fetched fresh, but can_read ignores user tenant. Mutation/inventory protections cannot guard this sink. Owner and recipient migration both reproduce disclosure. Verdict: confirmed.\n\nPost-fix adversarial pass: app/app.py:39-46 gates membership before owner shortcut, applies strict greater-than expiry, preserves revocation, and allows any independently live grant. Tests cover return migration and a fresh share after revocation. No new read or write path introduced. Do not treat synthetic authentication, storage, or trusted setup operations as vulnerabilities.\n\nCoverage critic: all four business endpoints and four framework documentation/schema routes are mapped. Both mutation sinks and inventory response were traced. No workers, outbound clients, persistence, templates or duplicate application files found. No unresolved candidates. Sequential review is less independent than a separate reviewer; delegation explicitly prohibited.\n')
print('Wrote findings and completed 50 coverage units.')
