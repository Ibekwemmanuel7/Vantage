# Vantage scope and portfolio boundary

Updated 17 October 2026.

Portfolio hub: [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US)

Portfolio map: [Product responsibilities](https://github.com/Ibekwemmanuel7/Lillie_US/blob/main/docs/PORTFOLIO.md)

## Domain and status

**Domain:** Southern US agriculture

**Status:** Design stage; no implementation or validated agriculture service.

## Current baseline

The initial market definition is documented. Vantage is a new product and does not copy CropSight or inherit its validation.

## Planned scope

First test: support an independent crop consultant prioritising field and zone inspections in irrigated upland cotton in Hale and Floyd counties, Texas. Proposed pilot: 3-5 growers and 20-40 fields, with farmer records and independent scouting. Broader crop, pasture and farm-water services require separate design and validation.

## Ownership and interfaces

Vantage owns farmer/adviser decisions and crop/pasture workflows. Vepris owns forestry. Velo can supply water context and Vaughan event flood/coastal layers; these interfaces are planned. Scouting support is not automatic irrigation control or a diagnosis.

## Delivery gate

Define the buyer, decision, last useful delivery time, reference data, baseline and acceptance criteria before implementation. Outputs must carry observation and processing dates, provenance, quality, uncertainty and unavailable-data states. Customer-provided records and assessments require explicit access control. No new operational or scientific performance claim follows from adding this roadmap.

The repository owns its reusable domain code, methods, tests and domain documentation. Lillie US owns cross-product integration, shared customer workflows, portfolio configuration and product-release coordination. Do not make this repository depend on Lillie US merely to create a backlink.
