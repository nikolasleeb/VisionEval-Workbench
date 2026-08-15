# Comparison Performance Notes

## Purpose and safety

These retained development measurements informed the SQLite comparison cache. The profiler and its API were removed from the end-user application; Compare always uses the authoritative VisionEval datastore path.

## Initial PlanRVA measurement

Measured July 21, 2026 on the development Intel Mac using the verified PlanRVA baseline and VisionEval 3.1.1 runtime. These are diagnostic samples, not a cross-machine benchmark.

| Selection | Rows | RDA cold | RDA warm | CSV cold | CSV warm | Parity |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Region / HvyTrkPCE / 2045 | 1 | 143 ms | 0.01 ms | 0.79 ms | 0.07 ms | Match |
| Vehicle / OwnCost / 2045 | 1,215,202 | 26.80 s | 0.28 s | 5.93 s | 4.57 s | Match |

The Vehicle RDA cold path broke down as follows:

| Phase | Time | Share of cold RDA time |
| --- | ---: | ---: |
| Decode `OwnCost.Rda` | 2.81 s | 10.5% |
| Decode stable key `VehId.Rda` | 23.68 s | 88.4% |
| Validate and align keys | 0.30 s | 1.1% |

The retained Vehicle CSV was 359.4 MB. The selected RDA variable and key files were 10.8 MB combined. All 1,215,202 keys and values matched.

## SQLite comparison cache

Compare now derives a disposable SQLite database per datastore, year, and table beneath `exchange/comparison-cache/v2/`. One batch R extractor loads the stable key and every missing requested variable, emits typed tabular streams, and imports them transactionally. Stable keys are stored once; variables retain typed values and five-decimal comparison values. RDA remains authoritative and retained CSV remains validation-only.

On the initial PlanRVA Vehicle/OwnCost cache build, the derived database was approximately 114 MB versus 359.4 MB for the retained CSV. After the database existed, the measured first page plus full statistics was 2.59 seconds; a repeated page in the same process was 0.18–0.21 seconds. Re-run these figures through the in-app profiler after packaging because filesystem and Docker state affect cold extraction.

The cache has a 5 GB least-recently-used limit. Active databases are pinned against eviction. Storage settings report cache size and expose Clear/Rebuild controls; deleting this derived data never deletes a datastore.

Removing a manually imported Workbench copy reads cache manifests and deletes only databases and completed operation artifacts that identify that datastore. Active operations block removal. Hiding an import does not delete or invalidate its cache.

## Interpretation

Stable-key RDA decoding is the dominant cold-path cost for large entity tables. Python alignment is comparatively small. CSV was 4.5 times faster than cold RDA in this sample, but it reparses a much larger file on every request. Cached RDA was about 16 times faster than the warm CSV parse.

The evidence supports extracting authoritative RDA once into the typed SQLite cache. It does not justify replacing datastore reads with CSV. CSV availability depends on export retention and may contain manual changes.

## Next measurements

- Repeat across Household, Worker, Azone, Bzone, Marea, and multiple variable types.
- Capture peak resident memory for RDA decoding, JSON transfer, Python key maps, and CSV parsing.
- Separate R/Rscript process startup from RDA load and JSON serialization.
- Record batch extraction, SQLite import, page query, statistics, cache-hit, memory, and storage timings across all supported table types.
- Record cold filesystem cache and warmed filesystem cache separately on a clean, idle machine.
