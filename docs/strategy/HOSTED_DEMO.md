# Vantage hosted demonstration

Vantage joins LillieWatch and LillieOre on the Lillie Earth website as a separate
agriculture product at `/vantage/`. Uganda is the first pilot, not the product identity.

The website repository is `Ibekwemmanuel7/pipelinewatch-ng`; its Cloudflare
configuration serves `landing/`. This release does not change the production
LillieWatch backend or the LillieOre portal.

Build into a new empty directory with:

```powershell
python scripts/build_hosted_demo.py outputs/hosted-release
```

The export allowlists workspace, field-review and report files, two public JSON
snapshots and two checksum-verified public historical PNG previews. Generated
imagery stays outside this repository's Git history. The hosting repository
contains the intentionally published static release. `release.json` records
the snapshot and every exported file checksum. Copy the bundle to
`landing/vantage/` in the hosting repository and use its normal deployment.

The exporter replaces the two Python preview API URLs with relative static
assets. Research navigation opens an explicit static status page. It does not
copy QA fixtures, databases, raw satellite imagery, model weights, private
review packets, credentials or the Python research service.

The demonstration's evidence cutoff is 5 June 2023. It provides no live alerts,
validated field recommendations, production yield forecast, diagnosis or
irrigation prescription. Browser-local notes are not cloud records; local
storage is shared across pages on this origin, so do not enter sensitive
records on shared devices. Optional report review packets stay in memory.

Operational deployment still requires authentication, tenant isolation,
durable synchronization, current observations, verified boundaries and
independent field outcomes. Historical demo hosting does not close these gaps.

Verify the static build with `python -m unittest discover -s tests -p
test_hosted_demo.py`, the existing JavaScript model tests, a local HTTP preview
and the deployed `/vantage/`, imagery and reports routes. Never stage unrelated
hosting-repository work as part of a release.

## Release status · 4 November 2026

Hosting commit `931730ea` was pushed to `pipelinewatch-ng/main`; the homepage
change contains only the Vantage navigation entry. Existing uncommitted website
and backend work was preserved. The local subpath preview loaded the satellite
and vegetation-change layers; Reports verified 2/2 imagery checksums and built
the brief. The static export test and 27 JavaScript tests passed. The mobile
report preview had no document-width overflow.

Initial public verification returned HTTP 403 and a user visit returned 404.
Subsequent authenticated Cloudflare inspection confirmed hosting commit
`931730ea`, version `a89754fd`, ready and serving 100% of production traffic.
The public `/vantage/` workspace then loaded successfully, including its
557-pixel-wide satellite preview. The public Reports page verified 2/2 imagery
previews, built its brief and enabled HTML export. Cloudflare canonicalizes
`reports.html` to `/vantage/reports`; relative asset paths work there.

Public availability is now confirmed. No routing, authentication or security
settings were changed. Deployment timing is the likely explanation for the
earlier 404, but its exact cause was not independently established.
