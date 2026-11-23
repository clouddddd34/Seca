"""Validate the supplemental schedule check against sequential and atomic fixes."""
from pathlib import Path
import tempfile
import unittest
from eval.v2.check_concurrency import evaluate
from eval.v2.test_v2 import corrected

class ConcurrencyTests(unittest.TestCase):
    def test_sequential_guards_fail_and_serialized_workflow_passes(self):
        source=(Path(__file__).parent/'fixtures/checkout/app.py').read_text(encoding='utf-8')
        sequential=corrected('checkout',source)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'app.py'
            path.write_text(sequential,encoding='utf-8')
            result=evaluate(path)
            self.assertTrue(all(v['passes'] is False for v in result.values()),result)
            self.assertEqual(result['payment']['wallet_after']['balance'],8000)
            self.assertEqual(result['refund']['wallet_after']['balance'],11000)
            atomic=sequential.replace('from copy import deepcopy','from copy import deepcopy\nfrom threading import RLock\nfrom functools import wraps')
            atomic=atomic.replace('app = FastAPI()', '''app = FastAPI()
    lock = RLock()
    def serialized(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with lock:
                return function(*args, **kwargs)
        return wrapped''')
            lines=atomic.splitlines()
            for index in reversed(range(len(lines))):
                if lines[index].strip().startswith('@app.'):
                    lines.insert(index+1,'    @serialized')
            atomic_path=Path(temp)/'atomic.py'
            atomic_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
            result=evaluate(atomic_path)
            self.assertTrue(all(v['passes'] is True for v in result.values()),result)

if __name__=='__main__':
    unittest.main()
