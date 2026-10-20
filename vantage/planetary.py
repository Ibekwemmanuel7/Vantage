"""Bounded public Azure asset signing; tokens stay in memory, never manifests."""
from datetime import datetime, timezone
import re
import time
from urllib.parse import urlparse


class SourceAccessError(RuntimeError):
    pass


class ContainerSigner:
    def __init__(self, session, clock=None, pause=time.sleep):
        self.session=session
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.pause=pause
        self.cache={}

    def __call__(self, href):
        parsed=urlparse(href)
        host=parsed.hostname or ""
        if (parsed.scheme!="https" or not host.endswith(".blob.core.windows.net")
                or parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment):
            raise SourceAccessError("Unsigned HTTPS Azure blob asset required")
        account=host.removesuffix(".blob.core.windows.net")
        container=parsed.path.lstrip("/").split("/")[0]
        if not re.fullmatch(r"[a-z0-9]{3,24}",account) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]",container):
            raise SourceAccessError("Invalid storage account/container")
        key=(account,container)
        cached=self.cache.get(key)
        if cached and (cached[0]-self.clock()).total_seconds()>120:
            return href+"?"+cached[1]
        endpoint=f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{account}/{container}"
        for attempt in range(3):
            try:
                response=self.session.get(endpoint,timeout=30)
            except Exception:
                if attempt==2:raise SourceAccessError("Token connection failed") from None
                self.pause(attempt+1)
                continue
            if response.status_code==429 or response.status_code>=500:
                if attempt<2:
                    self.pause(attempt+1)
                    continue
            if response.status_code!=200:
                raise SourceAccessError(f"Token endpoint HTTP {response.status_code}")
            try:
                body=response.json()
                expires=datetime.fromisoformat(body["msft:expiry"].replace("Z","+00:00"))
                token=body["token"]
                if expires.tzinfo is None or (expires-self.clock()).total_seconds()<=120 or not isinstance(token,str) or "sig=" not in token:
                    raise ValueError()
            except Exception:
                raise SourceAccessError("Invalid or near-expired token response") from None
            self.cache[key]=(expires,token)
            return href+"?"+token
        raise SourceAccessError("Token retry budget exhausted")
