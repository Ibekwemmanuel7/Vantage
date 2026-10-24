# Regional context in the Vantage workspace

The independent regional panel shows the pinned JRC recurring calendar context
for the public Iganga, Lira and Kasese analyst boxes. The anchor is 2024, not the
current season. Seasons may end in 2025. Source retrieval in October 2026 does
not establish historical operational availability.

It does not attach calendars to imported fields or the Kween 2023 reconstruction,
change readiness, confirm crop identity or supply scouting priorities. Loading
errors remain visible without a substitute context. No field records are read
or exported by the public builder. Published zone names preserve source spelling.

Rebuild from the separately cached public source files:

```powershell
python scripts/build_regional_dashboard.py --zones outputs/research/2026-10-24/uganda-wfs-zones.geojson --calendar-archive outputs/research/2026-10-24/jrc_calendars.source
```

The builder verifies pinned source hashes, replays conservative polygon joins
and calendar conversion, and publishes only three hard-coded public study boxes
to `web/data/regional-context.json`. It never consumes private join packets.
GIS dependencies are in `requirements-field.txt`. The tracked snapshot lets the
dashboard display context without distributing raw GIS caches.

Checks: `node --test tests/test_regional_dashboard.cjs tests/test_workspace_model.cjs`.
These are software checks, not agricultural validation. Confirmed farm boundaries,
crop identity, planting dates and independent dated outcomes are still required.
