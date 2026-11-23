import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path('app').resolve()))
suite = unittest.defaultTestLoader.discover('app', pattern='test_app.py')
with Path('evidence/after-tests.txt').open('w') as log:
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    log.write(f'Python test exit status: {0 if result.wasSuccessful() else 1}\n')
print(Path('evidence/after-tests.txt').read_text())
raise SystemExit(0 if result.wasSuccessful() else 1)
