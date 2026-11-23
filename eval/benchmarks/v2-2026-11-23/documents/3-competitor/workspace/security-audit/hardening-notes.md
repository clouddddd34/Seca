1. app/app.py:28,57,71: consider security-event logging for denied access and share/revocation events when adapting this fixture for deployment; no exploit attributed to absent logging.
2. app/app.py:14-16: consider finite-number validation for expires_at; no cross-principal impact demonstrated from non-finite input, so no fix or vulnerability claimed.
