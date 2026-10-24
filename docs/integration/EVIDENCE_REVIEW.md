# Local research evidence review

24 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/build_evidence_review.py
```

Produces `outputs/evidence-review/report.html` and companion `evidence.json`.
The report is self-contained, with no remote scripts, image requests or JSON
fetches. It includes a study-box filter, native print/save-PDF control, source
hashes and a local evidence download link. It is an internal unreviewed research
artifact; no external sharing, publication or partner application integration
is performed. The existing customer dashboard and historical data remain intact.

The report presents:

- October 2026 optical observations at their frozen 23 October 00:00 UTC cutoff,
  with accepted fractions, pixel denominators and recomputed quality/freshness.
- Latest qualifying observations, all stale in the actual study boxes; accepted
  pixels are explicitly distinct from vegetation health.
- Four June 2023 Iganga and three June 2024 Lira sample dates, training disabled,
  with no observed NDVI fabricated beneath clouds.
- Zero independent processor exports evaluated in the supplied comparison.
- The optical-history regression's blocked gap validation and clear-transition
  validation MAE 0.0708 versus persistence 0.0606, without hiding negative results.
- Missing field outcomes/calendars, reprocessing/delivery limits and the absence
  of validated agricultural performance or an untouched final test.

The studies retain distinct dates and purposes. The October series is not
presented as today's field condition, and the historical samples are not a
current service. Radar samples are untrained; the earlier optical-history
regression is a separate fitted experiment. No field ranking or diagnosis follows.

Before writing, the builder verifies sample source reports and artifacts, recent
numerical artifacts, comparison parent identities and the model dataset manifest.
Source and builder hashes accompany the export. HTML labels are escaped and
the document blocks external resources with Content Security Policy. These checks
establish software traceability, not independent scientific validity.

Visual preview was attempted but rejected by the browser security policy because
local `file://` URLs are not permitted. No alternate browser/protocol workaround
was attempted. Structure, source data and escaping are checked; visual layout,
filter interaction and printed pagination were not browser-verified. The print
button is a convenience, not a claim of a visually validated PDF export.

Remaining dependencies: real authenticated processor exports, independent farmer
outcomes/calendars, untouched evaluation and partner/customer review. No irrigation
prescription, disease diagnosis, yield forecast or forestry module is added.

Verification: 109 focused tests passed. Report tests check recomputed freshness,
denominator consistency, rejection of promoted sample inputs, escaped labels and
preservation of negative model results. Existing scientific fixtures remain green;
these tests do not verify browser interaction, visual layout or agricultural skill.
