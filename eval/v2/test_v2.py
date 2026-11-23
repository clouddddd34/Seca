from pathlib import Path
import tempfile
import unittest
from eval.v2.check import evaluate

ROOT = Path(__file__).resolve().parent

def corrected(name, text):
    if name == 'documents':
        return text.replace('if doc["owner"] == name:', 'if user["tenant"] != doc["tenant"]:\n            return False\n        if doc["owner"] == name:').replace('and not s["revoked"]', 'and s["expires_at"] > time() and not s["revoked"]')
    if name == 'checkout':
        return text.replace('discount = 500', 'if body.coupon and (name, body.coupon) in app.state.used_coupons:\n            raise HTTPException(409)\n        discount = 500').replace('if order["state"] == "draft":', 'if order["state"] != "paid":')
    return text

class V2Tests(unittest.TestCase):
    def test_originals_and_reference_fixes(self):
        expected = {'documents': {'expired_share_denied','recipient_migration_denied','owner_migration_denied'},
                    'checkout': {'refund_once','coupon_once','normal_purchase','refund_keeps_coupon_consumed'}, 'portal': set()}
        for name, failures in expected.items():
            with self.subTest(fixture=name):
                path = ROOT / 'fixtures' / name / 'app.py'
                results = evaluate(path,name)
                self.assertEqual({k for k,v in results.items() if v is not True},failures,results)
                with tempfile.TemporaryDirectory() as directory:
                    candidate = Path(directory)/'app.py'
                    candidate.write_text(corrected(name,path.read_text(encoding='utf-8')),encoding='utf-8')
                    result = evaluate(candidate,name)
                    self.assertTrue(all(v is True for v in result.values()),result)

    def test_rejects_disabling_legitimate_access(self):
        for name in ('documents','checkout','portal'):
            with self.subTest(fixture=name), tempfile.TemporaryDirectory() as directory:
                path = ROOT/'fixtures'/name/'app.py'
                text = corrected(name,path.read_text(encoding='utf-8'))
                text = text.replace('return app', '@app.middleware("http")\n    async def deny(request, call_next):\n        from fastapi.responses import Response\n        return Response(status_code=403)\n\n    return app')
                candidate = Path(directory)/'app.py'
                candidate.write_text(text,encoding='utf-8')
                self.assertFalse(all(v is True for v in evaluate(candidate,name).values()))

if __name__ == '__main__':
    unittest.main()
