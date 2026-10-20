from datetime import datetime, timedelta, timezone
import unittest
from vantage.planetary import ContainerSigner,SourceAccessError


class Response:
    def __init__(self,status,body=None):self.status_code=status;self.body=body
    def json(self):return self.body


class Session:
    def __init__(self,responses):self.responses=list(responses);self.calls=0
    def get(self,*args,**kwargs):self.calls+=1;return self.responses.pop(0)


class SignerTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2024,1,1,tzinfo=timezone.utc)
        self.href='https://sentinel2l2a01.blob.core.windows.net/sentinel2-l2/scene.tif'
        self.body={'msft:expiry':(self.now+timedelta(hours=1)).isoformat(),'token':'sig=test-secret'}

    def test_container_cache_and_expiry_refresh(self):
        session=Session([Response(200,self.body),Response(200,{**self.body,'msft:expiry':(self.now+timedelta(hours=3)).isoformat()})])
        signer=ContainerSigner(session,lambda:self.now,pause=lambda _:None)
        self.assertIn('?sig=',signer(self.href));signer(self.href.replace('scene','other'))
        self.assertEqual(session.calls,1)
        self.now+=timedelta(minutes=59)
        signer(self.href);self.assertEqual(session.calls,2)

    def test_bounded_transient_retries(self):
        session=Session([Response(503),Response(429),Response(200,self.body)])
        signer=ContainerSigner(session,lambda:self.now,pause=lambda _:None)
        signer(self.href);self.assertEqual(session.calls,3)

    def test_bad_expiry_and_untrusted_hosts_rejected(self):
        session=Session([Response(200,{**self.body,'msft:expiry':self.now.isoformat()})])
        signer=ContainerSigner(session,lambda:self.now)
        with self.assertRaises(SourceAccessError):signer(self.href)
        for href in ('http://example.com/data','https://example.com/data',self.href+'?sig=secret'):
            with self.assertRaises(SourceAccessError):signer(href)

    def test_errors_do_not_expose_credentials(self):
        signer=ContainerSigner(Session([Response(403)]),lambda:self.now)
        with self.assertRaises(SourceAccessError) as caught:signer(self.href)
        self.assertNotIn('sig=',str(caught.exception))
        self.assertNotIn(self.href,str(caught.exception))
