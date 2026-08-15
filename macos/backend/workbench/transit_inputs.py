from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


TRANSIT_NORMALIZATION_RULE = "virginia-transit-service-v1"
NA_VALUES = {"", "na", "nan", "null", "none"}

FILE_GROUPS = {
    "marea_transit_fuel.csv": {
        "Van": ["VanPropDiesel", "VanPropGasoline", "VanPropCng"],
        "Bus": ["BusPropDiesel", "BusPropGasoline", "BusPropCng"],
        "Rail": ["RailPropDiesel", "RailPropGasoline"],
    },
    "marea_transit_powertrain_prop.csv": {
        "Van": ["VanPropIcev", "VanPropHev", "VanPropBev"],
        "Bus": ["BusPropIcev", "BusPropHev", "BusPropBev"],
        "Rail": ["RailPropIcev", "RailPropHev", "RailPropEv"],
    },
}

SERVICE_FIELDS = {
    "Van": ["DRRevMi", "VPRevMi"],
    "Bus": ["MBRevMi", "RBRevMi"],
    "RailElectric": ["MGRevMi", "SRRevMi", "HRRevMi"],
    "RailIce": ["CRRevMi"],
}


def _missing(value: Any) -> bool:
    return str(value or "").strip().lower() in NA_VALUES


def _number(value: Any) -> float:
    return 0.0 if _missing(value) else float(str(value).strip())


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def _write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def _key(row: dict[str, str]) -> tuple[str, str]:
    return str(row.get("Geo", "")).strip(), str(row.get("Year", "")).strip()


def validate_transit_inputs(input_dir: Path, overrides: dict[str, Path] | None = None, scenario: str = "Baseline") -> list[dict[str, Any]]:
    """Validate the global completeness rules enforced by VisionEval."""
    overrides = overrides or {}
    errors: list[dict[str, Any]] = []
    for filename, groups in FILE_GROUPS.items():
        path = overrides.get(filename, input_dir / filename)
        if not path.is_file():
            continue
        try:
            fields, rows = _read(path)
        except (OSError, csv.Error, UnicodeError) as exc:
            errors.append({"code": "transit-input-unreadable", "scenario": scenario, "file": filename, "message": f"{scenario}: could not read {filename}: {exc}"})
            continue
        for mode, names in groups.items():
            if not all(name in fields for name in names):
                continue
            complete_rows = 0
            missing_rows: list[tuple[str, str]] = []
            partial_rows: list[tuple[str, str]] = []
            invalid_sums: list[tuple[str, str]] = []
            for row in rows:
                missing = [_missing(row.get(name)) for name in names]
                if all(missing):
                    missing_rows.append(_key(row))
                elif any(missing):
                    partial_rows.append(_key(row))
                else:
                    complete_rows += 1
                    try:
                        if abs(sum(_number(row.get(name)) for name in names) - 1.0) > 0.01:
                            invalid_sums.append(_key(row))
                    except ValueError:
                        invalid_sums.append(_key(row))
            if partial_rows:
                errors.append({
                    "code": "transit-mode-partial", "scenario": scenario, "file": filename, "mode": mode,
                    "rows": len(partial_rows), "examples": partial_rows[:5],
                    "message": f"{scenario}: {filename} has {len(partial_rows)} partially populated {mode} row(s); every {mode} field must have a value or all must be NA.",
                })
            if complete_rows and missing_rows:
                errors.append({
                    "code": "transit-mode-mixed-global", "scenario": scenario, "file": filename, "mode": mode,
                    "rows": len(missing_rows), "examples": missing_rows[:5],
                    "message": f"{scenario}: {filename} mixes populated and NA {mode} rows. VisionEval requires the {mode} fields to be complete for every Marea or NA for every Marea. Rebuild regional assets with the updated Virginia package.",
                })
            if invalid_sums:
                errors.append({
                    "code": "transit-proportion-sum", "scenario": scenario, "file": filename, "mode": mode,
                    "rows": len(invalid_sums), "examples": invalid_sums[:5],
                    "message": f"{scenario}: {filename} has {len(invalid_sums)} {mode} row(s) whose populated proportions do not sum to 1.",
                })
    return errors


def normalize_virginia_transit_inputs(input_dir: Path) -> dict[str, Any]:
    """Complete only wholly missing Virginia transit groups using documented rules."""
    service_path = input_dir / "marea_transit_service.csv"
    if not service_path.is_file():
        return {"rule": TRANSIT_NORMALIZATION_RULE, "applied": False, "adjustments": []}
    _, service_rows = _read(service_path)
    services = {_key(row): row for row in service_rows}
    adjustments: list[dict[str, Any]] = []

    for filename, groups in FILE_GROUPS.items():
        path = input_dir / filename
        if not path.is_file():
            continue
        fields, rows = _read(path)
        counts: dict[tuple[str, str], int] = {}
        for row in rows:
            service = services.get(_key(row))
            if service is None:
                raise ValueError(f"{filename} has no matching marea_transit_service.csv row for {_key(row)}")
            for mode, names in groups.items():
                if not all(name in fields for name in names):
                    continue
                missing = [_missing(row.get(name)) for name in names]
                if not any(missing):
                    continue
                if not all(missing):
                    raise ValueError(f"{filename} has partially populated {mode} fields for {_key(row)}")
                if mode in {"Van", "Bus"}:
                    service_total = sum(_number(service.get(name)) for name in SERVICE_FIELDS[mode])
                    if service_total > 0:
                        raise ValueError(f"{filename} is missing {mode} fields for {_key(row)} despite nonzero {mode} service")
                    values = (["0", "1", "0"] if mode == "Van" else ["1", "0", "0"])
                    if filename.endswith("powertrain_prop.csv"):
                        values = ["1", "0", "0"]
                    rule = f"zero-service-{mode.lower()}-compatibility-default"
                elif filename == "marea_transit_fuel.csv":
                    values = ["1", "0"]
                    rule = "rail-hydrocarbon-share-diesel"
                else:
                    electric = sum(_number(service.get(name)) for name in SERVICE_FIELDS["RailElectric"])
                    ice = sum(_number(service.get(name)) for name in SERVICE_FIELDS["RailIce"])
                    total = electric + ice
                    values = ["1", "0", "0"] if total <= 0 else [f"{ice / total:.12g}", "0", f"{electric / total:.12g}"]
                    rule = "rail-service-mile-electric-commuter-ice-share" if total > 0 else "zero-service-rail-compatibility-default"
                for name, value in zip(names, values):
                    row[name] = value
                counts[(mode, rule)] = counts.get((mode, rule), 0) + 1
        if counts:
            _write(path, fields, rows)
            adjustments.extend({"file": filename, "mode": mode, "rule": rule, "rows": count} for (mode, rule), count in sorted(counts.items()))

    errors = validate_transit_inputs(input_dir)
    if errors:
        raise ValueError("; ".join(error["message"] for error in errors))
    return {"rule": TRANSIT_NORMALIZATION_RULE, "applied": bool(adjustments), "adjustments": adjustments}
