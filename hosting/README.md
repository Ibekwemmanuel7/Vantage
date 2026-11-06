# Hosted demonstration access

The Cloudflare host gates the entire `/vantage` and `/vantage/*` namespace,
including reports, evidence JSON, imagery and release metadata. It uses the
existing `DEMO_PASSCODE` Cloudflare secret used for LillieWatch. No passcode is
stored in this repository. Vantage has a separate seven-day Secure, HttpOnly,
SameSite=Lax cookie; authenticated responses use private, no-store caching.
Missing configuration fails closed. Public website routes remain public.

`demo_gate_worker.js` and `wrangler.toml` mirror the hosting repository's gate
configuration. Both must be deployed together: `run_worker_first` is essential
because Cloudflare serves matching static assets directly otherwise.

Verification: `node --test tests/test_access_gate.cjs`.

This is the same shared-passcode demonstration access model as LillieWatch.
It is not individual user authentication or tenant isolation. The local Python
preview is unchanged and should stay bound to localhost. Previously downloaded
reports and copies already present in public Git history cannot be revoked by
this gate. Logout: `/vantage/__logout`. Rotating DEMO_PASSCODE invalidates both
products' sessions.
