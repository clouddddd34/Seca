"""Capture unittest's real exit status without PowerShell stderr conversion."""
import json
import sys
import unittest
from pathlib import Path
import fastapi
import httpx
import pydantic

sys.path.insert(0, str(Path('app').resolve()))
suite = unittest.defaultTestLoader.discover('app', pattern='test_security.py')
with Path('security-audit/fixed-tests.txt').open('w') as output:
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
print(Path('security-audit/fixed-tests.txt').read_text())
Path('security-audit/runtime.json').write_text(json.dumps({
    'python': sys.version, 'fastapi': fastapi.__version__, 'httpx': httpx.__version__,
    'pydantic': pydantic.__version__, 'tests_run': result.testsRun,
    'failures': len(result.failures), 'errors': len(result.errors),
}, indent=2) + '\n')
raise SystemExit(0 if result.wasSuccessful() else 1)
