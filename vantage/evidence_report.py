"""Human-readable research report; never a farmer recommendation or live service."""
from collections import Counter
from html import escape
import math
from vantage.recent_pixels import observation_quality,summarize_sequence


def summarize(recent,samples,comparison,model):
    if samples["training_eligible"] is not False or samples["model_trained"] is not False:
        raise ValueError("This report supports gated, untrained radar samples only")
    observations=[]
    for row in recent["observations"]:
        if row["status"]!="processed":raise ValueError("Complete recent numerical sequence required")
        quality=observation_quality(row["metrics"],row["acquired_at"],recent["decision_cutoff"])
        fraction=row["metrics"]["usable_fraction"]
        if not math.isfinite(fraction) or not 0<=fraction<=1 or abs(fraction-quality["usable_fraction"])>1e-8:
            raise ValueError("Coverage disagrees with pixel denominator")
        observations.append(dict(location_id=row["location_id"],acquired_at=row["acquired_at"],
            valid_pixels=row["metrics"]["valid_pixels"],total_pixels=row["metrics"]["total_pixels"],
            quality=quality,status="processed"))
    counts=Counter(r["partition"] for r in samples["samples"])
    optical_summary=summarize_sequence(observations)
    validation=model["clear_transition_diagnostics"]["validation"]
    return dict(schema_version="vantage-review-report-1",product="Vantage",selected_pilot="Uganda",
        mode="historical_research",decision_cutoff=recent["decision_cutoff"],
        independent_field_outcomes=recent["independent_field_outcomes"],
        optical_summary=optical_summary,observations=observations,
        fresh_qualified_boxes=sum(r["status"]=="recent_whole_box_research" for r in optical_summary),
        sample_dataset_id=samples["dataset_id"],sample_counts=dict(counts),
        training_eligible=False,radar_assisted_model_trained=False,blockers=samples["blockers"],
        independent_exports_evaluated=comparison["exported_acquisitions_evaluated"],
        learned_baseline=dict(status=model["promotion_status"],training_samples=model["model"]["training_samples"],
            training_dates=model["model"]["training_target_dates"],
            supported_gap_validation_dates=model["supported_validation_dates"],
            clear_transition_validation_pairs=validation["predicted_pixel_date_pairs"],
            clear_transition_learned_mae=validation["learned_mae"],
            clear_transition_persistence_mae=validation["persistence_mae"]),
        limitations=["Study boxes are not confirmed farmer fields or crop cohorts",
            "Recent October 2026 observations and historical June 2023/2024 samples are separate studies",
            "Missing optical values remain missing; radar estimates are not measured NDVI",
            "Quality-screened radar is not certified illumination or agricultural validity",
            "No disease diagnosis, irrigation prescription, validated yield forecast or farmer outcome claim",
            "Later-reprocessed historical imagery does not establish contemporaneous delivery availability",
            "No untouched final evaluation; development results have already been inspected"])


def render(data):
    e=lambda value:escape(str(value))
    comma=lambda value:f"{value:,}"
    summary_rows="".join(f'<tr><th scope="row">{e(r["location_id"])}</th><td>{e(r["latest_qualified_acquisition"] or "Unavailable")}</td><td>{e(round(r["qualified_age_at_cutoff_days"],2) if r["qualified_age_at_cutoff_days"] is not None else "Unavailable")}</td><td>{e(r["status"].replace("_"," "))}</td></tr>' for r in data["optical_summary"])
    rows=""
    for r in sorted(data["observations"],key=lambda r:(r["location_id"],r["acquired_at"])):
        q=r["quality"]
        rows+=f'<tr data-location="{e(r["location_id"])}"><th scope="row">{e(r["location_id"])}</th><td>{e(r["acquired_at"][:10])}</td><td><span class="bar" aria-hidden="true"><span style="width:{q["usable_fraction"]*100:.3f}%"></span></span>{q["usable_fraction"]:.1%}</td><td>{comma(r["valid_pixels"])} / {comma(r["total_pixels"])}</td><td>{e(q["state"].replace("_"," "))}</td></tr>'
    options="".join(f'<option value="{e(r["location_id"])}">{e(r["location_id"])}</option>' for r in data["optical_summary"])
    limitations="".join(f'<li>{e(s)}</li>' for s in data["limitations"])
    blockers="".join(f'<li>{e(s.replace("_"," "))}</li>' for s in data["blockers"])
    sources="".join(f'<tr><th scope="row">{e(s["path"])}</th><td class="hash">{e(s["sha256"])}</td></tr>' for s in data.get("sources",[]))
    m=data["learned_baseline"]
    number=lambda value:f"{value:.4f}" if value is not None else "Unavailable"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Vantage · Evidence review</title><style>
:root{{font-family:system-ui,sans-serif;color:#203d34;background:#f5f6f0;line-height:1.6}}*{{box-sizing:border-box}}body{{margin:0}}header,main,footer{{max-width:1140px;margin:auto;padding:24px}}header{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #d4ddd2}}a{{color:#225c4a}}.brand{{font-size:26px;font-weight:750;text-decoration:none}}.context,.muted{{color:#5d6d64;font-size:14px}}h1{{font-size:clamp(30px,5vw,48px);line-height:1.15;letter-spacing:-1px;margin:12px 0}}h2{{font-size:23px;line-height:1.3}}.eyebrow{{font-size:12px;font-weight:750;letter-spacing:2px}}.notice{{background:#fff3d9;border:1px solid #e9c77f;padding:18px;border-radius:10px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 0}}.card,section{{background:white;border:1px solid #d9dfd6;border-radius:12px;padding:24px}}.card strong{{display:block;font-size:36px;line-height:1.3}}section{{margin:24px 0}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:12px 10px;text-align:left;border-bottom:1px solid #e5e9e0;vertical-align:top}}thead th{{font-size:12px;color:#5d6d64}}tbody th{{font-weight:600}}.bar{{display:inline-block;vertical-align:middle;background:#edf0e9;width:85px;height:9px;border-radius:5px;margin-right:10px;overflow:hidden}}.bar span{{display:block;background:#8c7342;height:100%}}button,select{{font:inherit;background:white;border:1px solid #9aaa9e;border-radius:6px;padding:9px 14px;color:#203d34}}button{{cursor:pointer}}:focus-visible{{outline:3px solid #b17e19;outline-offset:3px}}.tools{{display:flex;gap:14px;flex-wrap:wrap;align-items:center}}.status{{font-weight:700;color:#815c15}}.hash{{font:12px monospace;word-break:break-all}}li{{margin:8px 0}}.cols{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}footer{{font-size:13px}}@media(max-width:700px){{.cards,.cols{{grid-template-columns:1fr}}header{{align-items:flex-start;gap:15px}}section{{padding:16px}}}}@media print{{button,select,.filter-label{{display:none}}body{{background:white}}section,.card{{break-inside:avoid}}.cards{{grid-template-columns:repeat(3,1fr)}}header,main,footer{{max-width:none}}tr[hidden]{{display:table-row}}}}
</style></head><body><header><div><a class="brand" href="https://github.com/Ibekwemmanuel7/Vantage">vantage</a><div class="context">Agricultural evidence · Selected pilot: Uganda</div></div><div class="tools"><a href="evidence.json" download>Evidence JSON</a><button id="print" type="button">Print / save PDF</button></div></header>
<main><p class="eyebrow">RESEARCH REVIEW · UNREVIEWED DRAFT</p><h1>What the evidence supports today.</h1><p>Acquisition coverage, research samples and model limitations in one traceable record.</p>
<div class="notice"><strong>Historical research. Not a live scouting recommendation.</strong><br>Optical cutoff: {e(data["decision_cutoff"])}. Report compiled: {e(data.get("generated_at","not recorded"))}. Dates and studies below are separate.</div>
<div class="cards"><article class="card"><span>Fresh, coverage-qualified study boxes</span><strong>{data["fresh_qualified_boxes"]} / {len(data["optical_summary"])}</strong><span class="muted">At the frozen October cutoff; not today's field status</span></article><article class="card"><span>Historical radar–optical sample dates</span><strong>{sum(data["sample_counts"].values())}</strong><span class="muted">{data["sample_counts"].get("train",0)} training references · {data["sample_counts"].get("validation",0)} validation references</span></article><article class="card"><span>Independent processor exports evaluated</span><strong>{data["independent_exports_evaluated"]}</strong><span class="muted">Comparisons remain separate from agricultural validation</span></article></div>
<section><h2>Where observations are too old</h2><p>Coverage gate: 70% of the whole study grid. Freshness limit: seven days. These are research rules, not validated crop thresholds.</p><div class="scroll"><table><caption>Latest coverage-qualified optical acquisition per study box</caption><thead><tr><th>Study box</th><th>Acquisition, UTC</th><th>Age at cutoff, days</th><th>Evidence state</th></tr></thead><tbody>{summary_rows}</tbody></table></div></section>
<section><h2>Observation coverage</h2><p>Bars represent accepted optical pixels, not vegetation health. A recent cloudy acquisition does not refresh the last usable observation.</p><div class="tools"><label class="filter-label" for="location">Study box</label><select id="location"><option value="all">All study boxes</option>{options}</select><span id="filter-status" role="status"></span></div><div class="scroll"><table><caption>Dated whole-box quality observations</caption><thead><tr><th>Study box</th><th>Acquisition</th><th>Accepted fraction</th><th>Accepted / total pixels</th><th>State at cutoff</th></tr></thead><tbody id="observations">{rows}</tbody></table></div></section>
<section><h2>Radar–optical sample readiness</h2><p class="status">Training disabled · No radar-assisted model trained</p><div class="cols"><div><p>Dataset <span class="hash">{e(data["sample_dataset_id"])}</span></p><p>June 2023 Iganga and June 2024 Lira references retain observed NDVI separately from radar features. Missing optical values remain unlabeled.</p></div><div><strong>Unresolved gates</strong><ul>{blockers}</ul></div></div></section>
<section><h2>The learned baseline has not cleared validation</h2><p>The earlier optical-history regression used {comma(m["training_samples"])} sampled transitions from {m["training_dates"]} target dates. It is separate from the untrained radar samples above.</p><p class="status">{m["supported_gap_validation_dates"]} supported transferred-gap validation dates</p><div class="scroll"><table><caption>Clear-transition validation diagnostic, not actual-cloud reconstruction</caption><thead><tr><th>Method</th><th>NDVI mean absolute error</th><th>Supported pixel-date pairs</th></tr></thead><tbody><tr><th>Learned regression</th><td>{number(m["clear_transition_learned_mae"])}</td><td>{comma(m["clear_transition_validation_pairs"])}</td></tr><tr><th>Last clear observation</th><td>{number(m["clear_transition_persistence_mae"])}</td><td>{comma(m["clear_transition_validation_pairs"])}</td></tr></tbody></table></div><p>Lower error is better. Supported subsets do not characterize withheld pixels, and neighboring pixel-date pairs are not independent farmers.</p></section>
<section><h2>Limits that stay with the report</h2><p><strong>{data["independent_field_outcomes"]} independent field outcomes recorded.</strong> Farmer usefulness and agricultural accuracy remain unvalidated.</p><ul>{limitations}</ul></section>
<section><details><summary><strong>Source records and integrity checks</strong></summary><p>Builder verifies source reports and referenced sample artifacts. Hashes support traceability; they do not establish independent scientific validity.</p><div class="scroll"><table><caption>Input report identities</caption><thead><tr><th>Record</th><th>SHA-256</th></tr></thead><tbody>{sources}</tbody></table></div></details></section>
</main><footer>Vantage · Part of <a href="https://github.com/Ibekwemmanuel7/Lillie_US">Lillie US</a>. Uganda is the selected pilot, not the product boundary. Forestry remains with Vepris. No CropSight validation transfers.</footer>
<script>document.getElementById('print').addEventListener('click',()=>window.print());document.getElementById('location').addEventListener('change',event=>{{let count=0;document.querySelectorAll('#observations tr').forEach(row=>{{row.hidden=event.target.value!=='all'&&row.dataset.location!==event.target.value;if(!row.hidden)count++;}});document.getElementById('filter-status').textContent=count+' observations shown';}});</script></body></html>'''
