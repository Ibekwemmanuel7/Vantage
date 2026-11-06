const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../hosting/demo_gate_worker.js'), 'utf8');
const worker = import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const env = { DEMO_PASSCODE: 'test-only-password', ASSETS: { fetch: async req => new Response(new URL(req.url).pathname) } };
async function request(route, options={}, config=env) {
  return (await worker).default.fetch(new Request('https://example.test'+route, options), config);
}
test('all Vantage routes and assets require access, including direct report and data links', async () => {
  for (const route of ['/vantage', '/vantage/', '/vantage/workspace', '/vantage/reports.html', '/vantage/data/scouting.json', '/vantage/assets/kween-rgb.png', '/vantage/release.json']) {
    const res=await request(route);
    assert.equal(res.status,401,route);
    assert.equal(res.headers.get('cache-control'),'no-store');
    assert.match(await res.text(), /action="\/vantage\/__login"/);
  }
});
test('Vantage login, private content and logout use separate secure cookie', async () => {
  const denied=await request('/vantage/__login',{method:'POST',body:new URLSearchParams({passcode:'wrong'})});
  assert.equal(denied.status,401);
  const login=await request('/vantage/__login',{method:'POST',body:new URLSearchParams({passcode:env.DEMO_PASSCODE})});
  assert.equal(login.status,303);
  assert.equal(login.headers.get('location'),'/vantage/');
  const cookie=login.headers.get('set-cookie');
  assert.match(cookie,/^lillie_vantage=/);
  assert.match(cookie,/Path=\/vantage;.*HttpOnly; Secure; SameSite=Lax/);
  const auth={headers:{Cookie:cookie.split(';')[0]}};
  const report=await request('/vantage/reports.html',auth);
  assert.equal(report.status,200);
  assert.equal(report.headers.get('cache-control'),'private, no-store');
  assert.equal(await report.text(),'/vantage/reports.html');
  assert.equal((await request('/demo/',auth)).status,401);
  const logout=await request('/vantage/__logout');
  assert.match(logout.headers.get('set-cookie'),/Max-Age=0/);
});
test('existing LillieWatch access and public website remain functional', async () => {
  const login=await request('/demo/__login',{method:'POST',body:new URLSearchParams({passcode:env.DEMO_PASSCODE})});
  const auth={headers:{Cookie:login.headers.get('set-cookie').split(';')[0]}};
  assert.equal(await (await request('/demo/',auth)).text(),'/demo/products');
  assert.equal((await request('/vantage/',auth)).status,401);
  assert.equal((await request('/',{})).status,200);
  assert.equal((await request('/vantage/',{}, {ASSETS:env.ASSETS})).status,503);
});
test('Cloudflare invokes worker before all protected static assets',()=>{
  const config=fs.readFileSync(path.join(__dirname,'../hosting/wrangler.toml'),'utf8');
  assert.match(config,/run_worker_first = \["\/demo", "\/demo\/\*", "\/vantage", "\/vantage\/\*"\]/);
});
