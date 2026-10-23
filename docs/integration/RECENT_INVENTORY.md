# Recent satellite catalog inventory

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

From the repository root:

```powershell
python scripts/inventory_recent.py --as-of 2026-10-23T00:00:00Z --days 21 --online
python scripts/inventory_recent.py --as-of 2026-10-23T00:00:00Z --days 21
```

The second command replays cached responses without network access. The tool
uses the existing three bounded Uganda study boxes from `uganda_archive.json`,
not customer fields or confirmed crop cohorts. UTC cutoff and a 1–31 day
lookback are required. Future cutoffs, out-of-window acquisitions, wrong
collections and paginated/truncated responses are rejected. A truncated query
must be narrowed rather than treated as complete. Existing archives are reused;
the command does not poll or silently overwrite prior catalog responses.

Source: [Microsoft Planetary Computer STAC](https://planetarycomputer.microsoft.com/api/stac/v1).
Raw responses and retrieval timestamps are archived under
`outputs/africa/recent/<plan-id>/`; the summary includes archive checksums.
These generated artifacts remain outside Git. Acquisition time is distinct
from catalog retrieval time; first historical availability remains unknown.

Actual run: the 21-day interval ending 23 October 2026 at 00:00 UTC returned
six catalog items each for Iganga, Lira and Kasese study boxes, without a next
page. The query counts are not unique acquisition-date counts or usable scenes.
An offline replay also completes. No pixels were downloaded or processed.

`usable_observation_status` remains `not_assessed` even for zero scene cloud
cover. Catalog bounding-box coverage does not prove usable pixels over crops.
The recent inventory never changes the frozen Kween dashboard or makes field
priorities available. It is not a real-time service or an EarthDaily connection.

Next gate: numerical reflectance processing, source masks and measured clear
coverage over appropriate agricultural/field boundaries, followed by confirmed
crop calendars and independent field findings. Yield, water allocation,
farmland-change and food-security outcome claims remain unsupported.

Verification: `python -m unittest tests.test_recent_inventory tests.test_archive tests.test_partner_bundle`.
Eleven tests passed, covering withheld usability, temporal bounds, collection
identity, truncated results and the historical bundle regression checks.
