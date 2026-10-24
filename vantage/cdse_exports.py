"""Bounded CDSE requests; secrets remain in memory and errors omit response bodies."""
from io import BytesIO
import json
import tarfile

TOKEN_URL="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_URL="https://sh.dataspace.copernicus.eu/process/v1"
MAX_BYTES=32*1024*1024


class ExportError(RuntimeError):pass


def export_files(raw):
    if len(raw)>MAX_BYTES:raise ExportError("Provider archive exceeds budget")
    files={}
    try:
        with tarfile.open(fileobj=BytesIO(raw),mode="r:") as archive:
            for member in archive:
                if member.name not in {"default.tif","userdata.json"} or not member.isfile() or member.name in files:
                    raise ExportError("Unexpected provider archive member")
                if not 0<member.size<=MAX_BYTES:raise ExportError("Invalid provider member size")
                files[member.name]=archive.extractfile(member).read()
    except (tarfile.TarError,OSError) as error:
        raise ExportError("Invalid provider archive") from None
    if set(files)!={"default.tif","userdata.json"}:raise ExportError("Provider outputs incomplete")
    try:json.loads(files["userdata.json"])
    except (ValueError,UnicodeError):raise ExportError("Provider metadata is not JSON") from None
    return files


def access_token(session,client_id,client_secret):
    if not client_id or not client_secret:raise ExportError("Explicit OAuth credentials required")
    try:
        response=session.post(TOKEN_URL,data=dict(grant_type="client_credentials",client_id=client_id,client_secret=client_secret),
                              timeout=45,allow_redirects=False)
        if response.status_code!=200:raise ExportError(f"Token endpoint HTTP {response.status_code}")
        body=response.json()
        token=body.get("access_token")
        if not isinstance(token,str) or not token.strip() or body.get("token_type","").lower()!="bearer":
            raise ExportError("Invalid bearer token response")
        return token
    except ExportError:raise
    except Exception:raise ExportError("Token request failed") from None


def process_export(session,token,request):
    # No automatic POST retry: a repeated processing request may consume quota.
    try:
        response=session.post(PROCESS_URL,json=request,
            headers={"Authorization":"Bearer "+token,"Accept":"application/tar"},
            stream=True,timeout=(30,180),allow_redirects=False)
        try:
            if response.status_code!=200:raise ExportError(f"Process endpoint HTTP {response.status_code}; not retried")
            if response.headers.get("Content-Type","").split(";")[0].lower() not in {"application/tar","application/x-tar"}:
                raise ExportError("Expected provider TAR response")
            chunks=[]
            size=0
            for chunk in response.iter_content(65536):
                size+=len(chunk)
                if size>MAX_BYTES:raise ExportError("Provider response exceeds byte budget")
                chunks.append(chunk)
            return export_files(b"".join(chunks))
        finally:response.close()
    except ExportError:raise
    except Exception:raise ExportError("Provider processing failed; not retried") from None
