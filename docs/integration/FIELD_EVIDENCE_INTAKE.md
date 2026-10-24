# Private field evidence intake

Vantage now validates locally supplied scouting, planting and harvest records.
This is an offline intake tool, not a collection service or a verified label registry.
Uganda is the first pilot; the contract contains no country-specific assumptions.
Actual independently verified field outcomes remain **zero**.

Start with `configs/field_evidence_template.json`, copy it into an ignored private
directory, and populate `records` with objects using these fields:

| Fields | Requirement |
| --- | --- |
| `record_id`, `field_id` | Stable pseudonymous record and field identifiers |
| `boundary_ref`, `boundary_version` | Reference to the boundary used for the observation and its version |
| `season_id`, `crop` | Declared season and crop; declarations are not confirmed calendars |
| `record_type` | `scouting`, `planting` or `harvest` |
| `source_kind` | `field_observation`, `farm_record`, `public_report` or `draft` |
| `source_ref`, `observer_ref` | Traceable source and pseudonymous observer references |
| `permission_status` | Must be `approved` for manual-review readiness |
| `observed_at`, `received_at`, `reviewed_at` | ISO timestamps with timezones, ordered and no later than validation time |
| `reviewer_ref` | Nonempty reviewer reference different from observer reference |
| `finding` | Scouting only: `useful_finding`, `no_useful_finding`, `uncertain` |

For harvest records, add a `harvest` object with positive numeric `mass` and
`area`; `mass_unit` is `kg` or `t`, `area_unit` is `ha` or `m2`. Supply
`measurement_ref`, `measurement_method`, explicit `moisture_basis`, and `extent`
(`partial` or `whole_field`). The derived tonnes/hectare is a unit conversion
for that submitted harvested area and stated moisture basis, not a satellite
yield estimate, moisture correction, or extrapolation to the whole field.
Different moisture bases must not be pooled without a separate protocol.

```powershell
python scripts/validate_field_evidence.py configs/field_evidence_template.json --out outputs/private/intake-empty-check.json
```

The blank template contains no invented observations. This check reports zero
records and no admitted labels. Outputs must resolve beneath `outputs/private`,
are exclusively created (existing reports are never overwritten), and include
the exact input SHA-256 and validation time. The metadata report omits source
IDs and free text, but must still remain private. Local files are not encrypted
and access, consent documentation, retention and deletion remain operator duties.

Internet posts are leads for investigation. Even a complete public-report record
is withheld for field follow-up. An `independently_verified` declaration cannot
override this gate. A distinct reviewer identifier cannot establish that two
people are independent or that permission, boundaries or findings are genuine.
References are checked for presence, not fetched or authenticated.

All records remain `training_eligible=false` and `evaluation_eligible=false`.
Manual-review readiness means the intake declarations are complete only.
Next steps require auditing original sources and boundary/season linkage,
confirming crop calendars and measurement protocols, freezing prospective
predictions, and assembling independent outcomes under the
[evaluation protocol](../africa/EVALUATION.md). Planting intake does not replace
the seasonal calendar approval contract; no automatic conversion is supplied.
Missing visits are never negative outcomes. No imagery-only diagnosis or
irrigation prescription is produced.
