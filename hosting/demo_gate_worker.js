// Lillie Earth website Worker: serves the static site from ./landing and
// protects /demo/ and /vantage/ with the demonstration passcode.
// The passcode is NOT in this file. Set it in Cloudflare as a secret named DEMO_PASSCODE.

const COOKIE = "lillie_demo";
const DAYS = 7;

async function token(env, namespace = "demo") {
  const data = new TextEncoder().encode(`lillie-${namespace}:` + (env.DEMO_PASSCODE || ""));
  const h = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, "0")).join("");
}

function hasCookie(req, value, cookie = COOKIE) {
  const c = req.headers.get("Cookie") || "";
  return c.split(/;\s*/).some(p => p === cookie + "=" + value);
}

function loginPage(msg, root = "/demo") {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Lillie Earth Demonstration</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:'Times New Roman',Times,serif;color:#f3efe6;
background:linear-gradient(rgba(8,12,22,.82),rgba(8,12,22,.92)),url(/demo/assets/img/bg1.jpg) center/cover}
.box{background:rgba(21,36,64,.92);border:1px solid #2a3d62;border-top:5px solid #c9a24a;border-radius:14px;padding:34px 38px;width:min(420px,90vw);text-align:center}
.t1{letter-spacing:5px;color:#c9a24a;font-weight:700;font-size:14px}.t2{font-style:italic;color:#a9b4c7;font-size:13px;margin:4px 0 22px}
h1{font-size:24px;margin:0 0 6px}p{color:#a9b4c7;margin:0 0 18px;font-size:15px}
input{width:100%;box-sizing:border-box;padding:11px 12px;border-radius:8px;border:1px solid #2a3d62;background:#0e1a2e;color:#f3efe6;font:18px 'Times New Roman',serif;text-align:center;letter-spacing:3px}
button{margin-top:14px;width:100%;padding:11px;border:0;border-radius:8px;background:#c9a24a;color:#0b1424;font:700 17px 'Times New Roman',serif;cursor:pointer}
.err{color:#e2553f;margin-top:12px;font-size:14px}
</style></head><body><form class="box" method="POST" action="${root}/__login">
<div class="t1">LILLIE EARTH INTELLIGENCE</div><div class="t2">Indigenous Space Intelligence for National Security and Economic Growth</div>
<h1>Demonstration access</h1><p>Enter the passcode you were given.</p>
<input type="password" name="passcode" autocomplete="current-password" autofocus required>
<button type="submit">Open demonstration</button>${msg ? `<div class="err">${msg}</div>` : ""}</form></body></html>`;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const p = url.pathname;
    const isDemo = p === "/demo" || p.startsWith("/demo/");
    const isVantage = p === "/vantage" || p.startsWith("/vantage/");
    if (!isDemo && !isVantage) return env.ASSETS.fetch(req);
    const root = isVantage ? "/vantage" : "/demo";
    const cookie = isVantage ? "lillie_vantage" : COOKIE;

    // The login page's own background image may load without the passcode.
    if (p === "/demo/assets/img/bg1.jpg") return env.ASSETS.fetch(req);

    if (!env.DEMO_PASSCODE) return new Response("Demonstration is not configured.", { status: 503, headers: { "Cache-Control": "no-store" } });
    const good = await token(env, isVantage ? "vantage" : "demo");

    if (p === `${root}/__login` && req.method === "POST") {
      const form = await req.formData();
      if ((form.get("passcode") || "").toString().trim() === env.DEMO_PASSCODE) {
        return new Response(null, { status: 303, headers: {
          "Location": `${root}/`,
          "Set-Cookie": `${cookie}=${good}; Path=${root}; Max-Age=${DAYS * 86400}; HttpOnly; Secure; SameSite=Lax`,
          "Cache-Control": "no-store" } });
      }
      return new Response(loginPage("Incorrect passcode. Please try again.", root), { status: 401, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
    }
    if (p === `${root}/__logout`) {
      return new Response(null, { status: 303, headers: { "Location": `${root}/`, "Set-Cookie": `${cookie}=; Path=${root}; Max-Age=0; HttpOnly; Secure; SameSite=Lax` } });
    }

    if (!hasCookie(req, good, cookie)) {
      return new Response(loginPage("", root), { status: 401, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow" } });
    }
    // Canonicalise only after authentication; all Vantage assets stay gated.
    if (p === "/vantage") return Response.redirect(new URL("/vantage/", url), 307);
    // /demo/ opens the products page; the full platform demo lives at /demo/platform.
    if (p === "/demo") return Response.redirect(new URL("/demo/", url), 307);
    if (p === "/demo/platform/") return Response.redirect(new URL("/demo/platform", url), 307);
    let target = null;
    if (p === "/demo/") target = "/demo/products";
    else if (p === "/demo/platform") target = "/demo/";
    const res = await env.ASSETS.fetch(target ? new Request(new URL(target, url), req) : req);
    const out = new Response(res.body, res);
    out.headers.set("Cache-Control", "private, no-store");
    out.headers.set("X-Robots-Tag", "noindex, nofollow");
    return out;
  }
};
