"""Payment processor contract and Razorpay/mock adapters. Card data never enters ERA."""
import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.request
import uuid

from core.config import Config
from core.errors import AppError, ValidationError


class PaymentGateway:
    def create_order(self, amount, currency, receipt): raise NotImplementedError
    def verify_payment(self, order_id, payment_id, signature): raise NotImplementedError
    def refund(self, payment_id, amount, receipt): raise NotImplementedError


class MockPaymentGateway(PaymentGateway):
    """Local-only adapter. Its simulated payment payload is intentionally not production-safe."""
    def __init__(self): self.secret=Config.SECRET_KEY.encode()

    def create_order(self,amount,currency,receipt):
        order_id="mock_order_"+uuid.uuid4().hex
        payment_id="mock_pay_"+uuid.uuid4().hex
        signature=hmac.new(self.secret,f"{order_id}|{payment_id}".encode(),hashlib.sha256).hexdigest()
        return {"id":order_id,"amount":int(amount*100),"currency":currency,"receipt":receipt,
                "mock_payment_id":payment_id,"mock_signature":signature,"gateway":"mock"}

    def verify_payment(self,order_id,payment_id,signature):
        expected=hmac.new(self.secret,f"{order_id}|{payment_id}".encode(),hashlib.sha256).hexdigest()
        return bool(signature) and hmac.compare_digest(expected,signature)

    def refund(self,payment_id,amount,receipt):
        return {"id":"mock_refund_"+uuid.uuid4().hex,"payment_id":payment_id,"amount":int(amount*100),"receipt":receipt,"status":"processed"}


class RazorpayAdapter(PaymentGateway):
    base_url="https://api.razorpay.com/v1"

    def __init__(self):
        if not Config.RAZORPAY_KEY_ID or not Config.RAZORPAY_KEY_SECRET:
            raise ValidationError("Razorpay credentials are not configured.")
        if not Config.RAZORPAY_KEY_ID.startswith("rzp_test_"):
            raise ValidationError("This adapter is restricted to Razorpay test-mode keys.")
        self.key_id=Config.RAZORPAY_KEY_ID; self.secret=Config.RAZORPAY_KEY_SECRET

    def _request(self,path,payload):
        auth=base64.b64encode(f"{self.key_id}:{self.secret}".encode()).decode()
        request=urllib.request.Request(self.base_url+path,data=json.dumps(payload).encode(),headers={"Authorization":"Basic "+auth,"Content-Type":"application/json"},method="POST")
        try:
            with urllib.request.urlopen(request,timeout=15) as response: return json.loads(response.read().decode())
        except (urllib.error.URLError,urllib.error.HTTPError) as exc:
            raise AppError(f"Payment gateway request failed: {exc}",502)

    def _get(self,path):
        auth=base64.b64encode(f"{self.key_id}:{self.secret}".encode()).decode()
        request=urllib.request.Request(self.base_url+path,headers={"Authorization":"Basic "+auth},method="GET")
        try:
            with urllib.request.urlopen(request,timeout=15) as response: return json.loads(response.read().decode())
        except (urllib.error.URLError,urllib.error.HTTPError) as exc:
            raise AppError(f"Payment gateway request failed: {exc}",502)

    def create_order(self,amount,currency,receipt):
        data=self._request("/orders",{"amount":int(amount*100),"currency":currency,"receipt":receipt})
        data["gateway"]="razorpay"; data["key_id"]=self.key_id
        return data

    def verify_payment(self,order_id,payment_id,signature):
        expected=hmac.new(self.secret.encode(),f"{order_id}|{payment_id}".encode(),hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(expected,signature): return False
        payment=self._get(f"/payments/{payment_id}")
        return payment.get("order_id")==order_id and payment.get("status")=="captured"

    def refund(self,payment_id,amount,receipt):
        return self._request(f"/payments/{payment_id}/refund",{"amount":int(amount*100),"notes":{"receipt":receipt}})


def get_gateway(choice=None):
    choice=choice or Config.PAYMENT_GATEWAY
    if choice=="mock": return MockPaymentGateway()
    if choice=="razorpay": return RazorpayAdapter()
    raise ValidationError("PAYMENT_GATEWAY must be 'mock' or 'razorpay'.")
