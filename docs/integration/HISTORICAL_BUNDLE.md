# Historical partner evidence example

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

Run `python scripts/export_partner_bundle.py` from the repository root.
Open `outputs/partner-example/report.html` and inspect its companion
`evidence.json`. No credentials or scientific runtime are required because
the exporter uses the existing public Kween historical snapshot.

This is a contract-discussion artifact, not the agreed partner API. It does not
implement authentication, map delivery, a report publication workflow or live
monitoring. The report is an unreviewed draft and publication is not authorized.
No private field records or browser notes enter the export.

Schema `vantage-partner-example-1` separates quality, the withheld decision,
unavailable outputs and original source evidence. Its deterministic SHA-256
bundle identifier hashes sorted JSON before adding the identifier itself;
this is a content identity, not a digital signature or independent validation.
The original snapshot identifier and run lineage remain available.

Freshness is recomputed at the frozen historical cutoff. Future optical
observations and an inconsistent latest usable observation are rejected.
No qualified observations means missing evidence, never healthy conditions.
Acquisition time does not establish when imagery became available; historical
delivery availability remains unknown. Radar does not refresh optical evidence.

The current Kween example remains stale, with no validated field priorities.
Crop identity, planting dates and independent field outcomes are still missing.
Source lineage and preview checksums are copied, but raster bytes are neither
bundled nor independently verified by this exporter. The existing local
dashboard retains its separate checksum-checked preview delivery.

Food security, yield/production, farmland change and water allocation remain
future independently evaluated modules. This export offers no diagnosis,
fertilizer/pesticide prescription or irrigation instruction. Forestry remains
with Vepris and no CropSight validation transfers.

Tests: `python -m unittest tests.test_partner_bundle tests.test_dashboard_http`.
These check software behavior, not agricultural accuracy or customer fit.
