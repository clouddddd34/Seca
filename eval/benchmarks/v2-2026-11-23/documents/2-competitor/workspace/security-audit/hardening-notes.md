# Hardening notes (not findings)

- app/app.py:28,57,71: structured authorization/share/revoke events could support operational investigation. No logging-based exploit demonstrated; no logging changes applied.
- app/app.py:58,73: mutation routes distinguish missing resources (404) from forbidden ones (403). Uniform concealment may be useful if identifier existence is confidential; README defines document access but no identifier secrecy contract. No document contents or share attributes are returned on these errors. No confidentiality impact beyond existence was established.
