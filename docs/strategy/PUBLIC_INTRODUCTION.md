# Public introduction · 5 November 2026

Vantage's hosted root is a product introduction. The scouting demonstration
is `/vantage/workspace` (Cloudflare may remove the `.html` suffix).
Reports and field review keep their existing routes and link back to the
workspace. Existing workspace-section root bookmarks redirect to the new
workspace. The Python local preview retains its existing dashboard at `/`;
`/landing.html` previews the introduction without changing that workflow.

The public page presents the agriculture product first, with Uganda as the
active pilot geography. Its interactive comparison uses the same two public
historical PNGs as the dashboard: Sentinel-2 on 26 May 2023 and NDVI difference
against 2019–2022 calendar context. The 5 June 2023 cutoff, staleness, locality
boundary limitation and zero independent field outcomes stay visible.

The comparison slider is keyboard accessible. Stock photos are decorative and
credited separately. The document illustration is explicitly illustrative;
Reports generates the actual brief. The pilot checklist downloads a planning
document, with no lead-submission form or implied monitoring agreement.

The source is `web/landing.html`, `landing.css`, `landing.js` and
`pilot-checklist.txt`. `build_hosted_demo.py` exports the public root and
workspace from these and existing dashboard sources, rewrites only local
navigation and the fixed snapshot preview URLs, and records the release hashes.
Scientific data, thresholds and model behaviour are unchanged.
