"""Resolve and archive authoritative Sentinel-1 product annotations via SAFE manifests."""

# ruff: noqa: E402
import argparse
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source
from vantage.archive import fingerprint
from vantage.imagery import atomic_json, sha256_file
from vantage.planetary import ContainerSigner


def product_references(text, manifest_href):
    root = ET.fromstring(text)
    references = []
    for node in root.iter():
        if node.tag.split("}")[-1] != "dataObject":
            continue
        rep = node.attrib.get("repID", "")
        for location in node.iter():
            if location.tag.split("}")[-1] != "fileLocation":
                continue
            href = location.attrib.get("href", "")
            if (
                "ProductSchema" in rep
                and "/annotation/" in "/" + href.lstrip("./")
                and "/calibration/" not in href
                and "/rfi/" not in href
            ):
                checksum = next(
                    (c for c in node.iter() if c.tag.split("}")[-1] == "checksum"), None
                )
                stream = next(
                    c for c in node.iter() if c.tag.split("}")[-1] == "byteStream"
                )
                if checksum is None or checksum.attrib.get("checksumName") != "MD5":
                    raise ValueError("Manifest product checksum required")
                references.append(
                    dict(
                        rep_id=rep,
                        href=urljoin(manifest_href, href),
                        md5=checksum.text.strip(),
                        size=int(stream.attrib["size"]),
                    )
                )
    return references


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-downloads", action="store_true")
    args = parser.parse_args()
    plan = json.loads((ROOT / "configs/kween_2023_viewing.json").read_text())
    parent_info = json.loads(
        (ROOT / "docs/africa/KWEEN_RADAR_PIXELS_RUN.json").read_text()
    )
    if parent_info["run_id"] != plan["parent_radar_run_id"]:
        raise ValueError("Pinned radar cohort differs")
    catalog_info = json.loads((ROOT / "docs/africa/KWEEN_RADAR_RUN.json").read_text())
    catalog_root = ROOT / "outputs/africa/radar" / catalog_info["plan_sha256"][:20]
    catalog = json.loads((catalog_root / "radar-catalog.json").read_text())["response"][
        "features"
    ]
    by_id = {i["id"]: i for i in catalog}
    root = ROOT / "outputs/africa/viewing" / fingerprint(plan)[:20]
    root.mkdir(parents=True, exist_ok=True)
    frozen = root / "frozen-plan.json"
    if not frozen.exists():
        atomic_json(
            frozen,
            dict(
                plan=plan,
                frozen_at=datetime.now(timezone.utc).isoformat(),
                scope="Fixed local geometry research, no complete shadow or illumination certification",
            ),
        )
    elif json.loads(frozen.read_text())["plan"] != plan:
        raise ValueError("Frozen viewing plan differs")
    signer = ContainerSigner(source.SESSION)
    rows = []
    if len(parent_info["observations"]) > plan["max_passes"]:
        raise ValueError("Annotation acquisition budget exceeded")
    for index, record in enumerate(parent_info["observations"]):
        rtc = by_id[record["item_id"]]
        links = [
            link["href"] for link in rtc["links"] if link.get("rel") == "derived_from"
        ]
        if len(links) != 1 or not links[0].startswith(
            "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-grd/items/"
        ):
            raise ValueError("Authoritative source GRD item link required")
        grd_path = root / f"{index}-grd.json"
        if not grd_path.exists():
            if not args.allow_downloads:
                raise FileNotFoundError("Source item not cached")
            response = source.SESSION.get(links[0], timeout=45)
            response.raise_for_status()
            atomic_json(grd_path, response.json())
        grd = json.loads(grd_path.read_text())
        manifest_href = grd["assets"]["safe-manifest"]["href"]
        manifest_path = root / f"{index}-manifest.xml"
        if not manifest_path.exists():
            if not args.allow_downloads:
                raise FileNotFoundError("SAFE manifest not cached")
            response = source.SESSION.get(signer(manifest_href), timeout=45)
            response.raise_for_status()
            manifest_path.write_bytes(response.content)
        refs = product_references(manifest_path.read_text(), manifest_href)
        # Match VV only after following actual manifest references, not guessed paths.
        selected = [
            r
            for r in refs
            if "vv" in urlparse(r["href"]).path.rsplit("/", 1)[-1].lower()
        ]
        if len(selected) != 1:
            raise ValueError(
                "Exactly one manifest-referenced VV product annotation required"
            )
        href = selected[0]["href"]
        annotation_path = root / f"{index}-product-vv.xml"
        if not annotation_path.exists():
            if not args.allow_downloads:
                raise FileNotFoundError("Product annotation not cached")
            response = source.SESSION.get(signer(href), timeout=45)
            if response.status_code == 404:
                # The host flattens original SAFE product filenames to the measurement stem.
                # Accept this single storage mapping only if original SAFE byte size/MD5 agree.
                measurement = grd["assets"]["vv"]["href"]
                href = (
                    measurement.replace("/measurement/", "/annotation/").rsplit(".", 1)[
                        0
                    ]
                    + ".xml"
                )
                response = source.SESSION.get(signer(href), timeout=45)
            response.raise_for_status()
            if (
                len(response.content) != selected[0]["size"]
                or hashlib.md5(response.content).hexdigest() != selected[0]["md5"]
            ):
                raise ValueError("Product annotation does not match SAFE checksum")
            annotation_path.write_bytes(response.content)
        raw = annotation_path.read_bytes()
        if (
            len(raw) != selected[0]["size"]
            or hashlib.md5(raw).hexdigest() != selected[0]["md5"]
        ):
            raise ValueError("Cached annotation differs from SAFE manifest")
        # The checksum pins the bytes even on offline replay; record the actual host mapping.
        measurement = grd["assets"]["vv"]["href"]
        mapped_href = (
            measurement.replace("/measurement/", "/annotation/").rsplit(".", 1)[0]
            + ".xml"
        )
        annotation = ET.fromstring(annotation_path.read_bytes())
        if annotation.tag.split("}")[-1] != "product":
            raise ValueError("Referenced XML is not a Sentinel-1 product annotation")
        rows.append(
            dict(
                item_id=record["item_id"],
                acquired_at=record["acquired_at"],
                track_id=record["track_id"],
                source_item_url=links[0],
                source_item=grd_path.name,
                source_item_sha256=sha256_file(grd_path),
                manifest=manifest_path.name,
                manifest_sha256=sha256_file(manifest_path),
                manifest_unsigned_href=manifest_href,
                annotation=annotation_path.name,
                annotation_sha256=sha256_file(annotation_path),
                annotation_unsigned_href=mapped_href,
                stac_product_asset_href=grd["assets"]
                .get("schema-product-vv", {})
                .get("href"),
                product_reference=selected[0],
            )
        )
        print(
            record["acquired_at"],
            annotation.tag,
            len(annotation.findall(".//geolocationGridPoint")),
            len(annotation.findall(".//orbit")),
            flush=True,
        )
    report = dict(
        schema_version="viewing-inputs-1",
        plan=plan,
        plan_sha256=fingerprint(plan),
        frozen_plan_sha256=sha256_file(frozen),
        source_catalog_sha256=sha256_file(catalog_root / "radar-catalog.json"),
        annotations=rows,
        code_sha256=sha256_file(ROOT / "scripts/acquire_viewing_annotations.py"),
    )
    atomic_json(root / "inputs.json", report)
    atomic_json(
        root.parent / "latest-inputs.json",
        dict(directory=root.name, manifest="inputs.json"),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit("Annotation acquisition failed: " + type(error).__name__)
