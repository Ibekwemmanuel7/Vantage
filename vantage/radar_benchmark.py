"""Processor comparison, never agricultural accuracy or illumination certification."""

import re
import numpy as np

PROVIDER_BANDS = ["localIncidenceAngle", "shadowMask", "dataMask"]


def scene_identity(metadata, expected):
    """Require the actual provider scene inventory, not a user assertion of identity."""
    ids = set()

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "sentinel1ProductId":
                    if not isinstance(child, str):
                        raise ValueError("Invalid provider scene identity")
                    ids.add(child.removesuffix(".SAFE"))
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(metadata.get("scenes", {}))
    if ids != {expected}:
        raise ValueError(
            "Provider scene inventory must contain exactly the pinned SAFE product"
        )
    version = metadata.get("inputMetadata", {}).get("serviceVersion")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("Provider service version is required")
    return dict(product_ids=sorted(ids), service_version=version)


def request_for(grid, product):
    """Credential-free Process API request; real service compatibility is unverified."""
    match = re.fullmatch(
        r"S1A_IW_GRDH_1SDV_(\d{8}T\d{6})_(\d{8}T\d{6})_\d{6}_[A-F0-9]{6}_[A-F0-9]{4}",
        product,
    )
    if not match:
        raise ValueError("Pinned S1A IW dual-polarization SAFE identity required")
    t = grid["transform"]
    if grid["crs"] != "EPSG:32636" or t[1] != 0 or t[3] != 0 or t[0] <= 0 or t[4] >= 0:
        raise ValueError("Unrotated metric Uganda grid required")

    def iso(value):
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}T{value[9:11]}:{value[11:13]}:{value[13:15]}Z"

    return dict(
        input=dict(
            bounds=dict(
                bbox=[
                    t[2],
                    t[5] + grid["height"] * t[4],
                    t[2] + grid["width"] * t[0],
                    t[5],
                ],
                properties=dict(crs="http://www.opengis.net/def/crs/EPSG/0/32636"),
            ),
            data=[
                dict(
                    type="sentinel-1-grd",
                    dataFilter=dict(
                        timeRange={"from": iso(match[1]), "to": iso(match[2])},
                        acquisitionMode="IW",
                        polarization="DV",
                        orbitDirection="ASCENDING",
                        resolution="HIGH",
                    ),
                    processing=dict(
                        orthorectify=True,
                        backCoeff="GAMMA0_TERRAIN",
                        demInstance="COPERNICUS_30",
                        radiometricTerrainOversampling=2,
                        upsampling="NEAREST",
                        downsampling="NEAREST",
                    ),
                )
            ],
        ),
        output=dict(
            width=grid["width"],
            height=grid["height"],
            responses=[
                dict(identifier="default", format=dict(type="image/tiff")),
                dict(identifier="userdata", format=dict(type="application/json")),
            ],
        ),
        evalscript="""//VERSION=3
function setup() {
  return {input: ["localIncidenceAngle", "shadowMask", "dataMask"],
          mosaicking: "ORBIT", output: {bands: 3, sampleType: "FLOAT32"}};
}
function evaluatePixel(samples) {
  if (samples.length !== 1) return [0, 0, 0];
  let s = samples[0];
  return [s.localIncidenceAngle, s.shadowMask, s.dataMask];
}
function updateOutputMetadata(scenes, inputMetadata, outputMetadata) {
  outputMetadata.userData = {scenes: scenes, inputMetadata: inputMetadata};
}
""",
    )


def compare(local_angle, local_class, sightline_class, provider, region):
    """All denominators explicit; guard/unknown never become clear or zero error.

    Shadow table is directional co-occurrence, not a truth confusion matrix.
    Incidence is compared wherever both angles are valid, including risky facets.
    """
    local_angle = np.asarray(local_angle)
    local_class, sightline_class = np.asarray(local_class), np.asarray(sightline_class)
    provider, region = np.asarray(provider), np.asarray(region)
    if (
        local_angle.ndim != 2
        or provider.shape != (3,) + local_angle.shape
        or region.shape != local_angle.shape
        or region.dtype.kind != "b"
        or local_class.shape != local_angle.shape
        or sightline_class.shape != local_angle.shape
    ):
        raise ValueError("Exactly aligned arrays and boolean region required")
    if (
        not np.isin(local_class, [0, 1, 2, 3, 4]).all()
        or not np.isin(sightline_class, [0, 1, 2, 3]).all()
    ):
        raise ValueError("Unknown local class encoding")
    angle, shadow, mask = provider
    if not np.isin(mask, [0, 1]).all():
        raise ValueError("Provider dataMask must explicitly be binary")
    valid = mask == 1
    if (
        not np.isfinite(angle[valid]).all()
        or ((angle[valid] < 0) | (angle[valid] > 180)).any()
        or not np.isin(shadow[valid], [0, 1]).all()
    ):
        raise ValueError("Invalid provider angles or shadow encoding on data pixels")
    available = region & valid
    local_valid = (
        np.isfinite(local_angle)
        & (local_angle >= 0)
        & (local_angle <= 180)
        & (local_class != 0)
    )
    angles = available & local_valid
    delta = (local_angle - angle)[angles]
    metrics = (
        None
        if not delta.size
        else dict(
            signed_median_degrees=float(np.median(delta)),
            mean_absolute_degrees=float(np.mean(np.abs(delta))),
            p95_absolute_degrees=float(np.percentile(np.abs(delta), 95)),
        )
    )
    comparable = available & np.isin(sightline_class, [1, 2])
    table = {
        f"vantage_{left}__provider_{right}": int(
            np.sum(comparable & (sightline_class == code) & (shadow == flag))
        )
        for code, left in ((1, "bounded_clear"), (2, "obstruction_risk"))
        for flag, right in ((0, "not_flagged"), (1, "near_shadow"))
    }
    return dict(
        region_pixels=int(region.sum()),
        provider_data_pixels=int(available.sum()),
        provider_missing_pixels=int(np.sum(region & ~valid)),
        incidence_comparable_pixels=int(angles.sum()),
        incidence_difference=metrics,
        sightline_comparable_pixels=int(comparable.sum()),
        sightline_unknown_pixels=int(np.sum(region & (sightline_class == 0))),
        sightline_guard_pixels=int(np.sum(region & (sightline_class == 3))),
        shadow_cooccurrence=table,
        status="compared" if delta.size or comparable.any() else "unavailable",
        equivalent_shadow_definitions=False,
        agricultural_accuracy_measured=False,
        radar_illumination_confirmed=False,
    )
