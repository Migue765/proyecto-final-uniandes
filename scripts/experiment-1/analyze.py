#!/usr/bin/env python3
"""Generate a deterministic, body-free summary from Experiment 1 JTL evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
REQUIRED_COLUMNS = {"timeStamp", "elapsed", "responseCode", "success"}
MAX_JSON_BYTES = 1024 * 1024
MAX_SAMPLES = 2_000_000


class EvidenceError(ValueError):
    """Raised when evidence does not satisfy the expected local contract."""


def utc_iso(epoch_ms: int) -> str:
    return (
        datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise EvidenceError(f"Missing regular evidence file: {path.name}")
    if path.stat().st_size > MAX_JSON_BYTES:
        raise EvidenceError(f"Evidence metadata is unexpectedly large: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceError(f"Invalid JSON evidence: {path.name}") from error
    if not isinstance(value, dict):
        raise EvidenceError(f"Expected a JSON object: {path.name}")
    return value


def positive_int(value: Any, name: str, maximum: int = 10_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvidenceError(f"{name} must be an integer")
    if value < 1 or value > maximum:
        raise EvidenceError(f"{name} is outside the supported range")
    return value


def parse_nonnegative_int(value: str, field: str, row_number: int) -> int:
    if not value.isdigit():
        raise EvidenceError(f"Invalid {field} in JTL row {row_number}")
    parsed = int(value)
    if parsed > 10**15:
        raise EvidenceError(f"Out-of-range {field} in JTL row {row_number}")
    return parsed


def percentile(values: list[int], quantile: float) -> int:
    """Return the nearest-rank percentile from a non-empty list."""
    ordered = sorted(values)
    rank = max(1, math.ceil(quantile * len(ordered)))
    return ordered[rank - 1]


def error_category(response_code: str, valid: bool) -> str | None:
    if valid:
        return None
    if response_code == "429":
        return "http_429"
    if response_code.isdigit():
        code = int(response_code)
        if 200 <= code <= 299:
            return "business_schema_or_assertion"
        if 400 <= code <= 499:
            return "http_4xx"
        if 500 <= code <= 599:
            return "http_5xx"
        return "other_http_status"
    if response_code.startswith("Non HTTP response code"):
        return "transport_or_timeout"
    return "other_failure"


def summarize_jtl(path: Path, target_rpm: int, measured_seconds: int) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise EvidenceError(f"Missing regular JTL file: {path}")

    timestamps: list[int] = []
    latencies: list[int] = []
    validities: list[bool] = []
    valid_count = 0
    errors: Counter[str] = Counter()
    minute_samples: dict[int, list[tuple[int, bool]]] = defaultdict(list)

    csv.field_size_limit(1024 * 1024)
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
                raise EvidenceError(f"JTL header is incomplete: {path}")
            for row_number, row in enumerate(reader, start=2):
                if len(timestamps) >= MAX_SAMPLES:
                    raise EvidenceError(f"JTL exceeds {MAX_SAMPLES} samples: {path}")
                timestamp = parse_nonnegative_int(row["timeStamp"], "timeStamp", row_number)
                elapsed = parse_nonnegative_int(row["elapsed"], "elapsed", row_number)
                success_text = row["success"].strip().lower()
                if success_text not in {"true", "false"}:
                    raise EvidenceError(f"Invalid success value in JTL row {row_number}")
                success = success_text == "true"
                response_code = row["responseCode"].strip()
                http_2xx = response_code.isdigit() and 200 <= int(response_code) <= 299
                valid = success and http_2xx

                timestamps.append(timestamp)
                latencies.append(elapsed)
                validities.append(valid)
                valid_count += int(valid)
                category = error_category(response_code, valid)
                if category is not None:
                    errors[category] += 1
    except (OSError, UnicodeError, csv.Error) as error:
        raise EvidenceError(f"Unable to parse JTL: {path}") from error

    if not timestamps:
        raise EvidenceError(f"JTL contains no samples: {path}")

    first_timestamp = min(timestamps)
    for timestamp, elapsed, valid in zip(timestamps, latencies, validities):
        minute_index = max(0, (timestamp - first_timestamp) // 60_000)
        minute_samples[minute_index].append((elapsed, valid))

    sample_count = len(timestamps)
    expected_samples = target_rpm * measured_seconds / 60
    tolerance_samples = expected_samples * 0.01
    attempted_rpm = sample_count * 60 / measured_seconds
    completed_rpm = valid_count * 60 / measured_seconds
    valid_percent = valid_count * 100 / sample_count
    latency = {
        "p50_ms": percentile(latencies, 0.50),
        "p95_ms": percentile(latencies, 0.95),
        "p99_ms": percentile(latencies, 0.99),
        "max_ms": max(latencies),
    }
    criteria = {
        "offered_rate_within_1_percent": abs(sample_count - expected_samples)
        <= tolerance_samples,
        # ASR-ESC-01 demands technical error strictly below 1 percent, so a run
        # that lands on exactly 99.0 percent valid responses is a FAIL.
        "valid_success_above_99_percent": valid_percent > 99.0,
        "p95_at_most_250_ms": latency["p95_ms"] <= 250,
        "p99_at_most_500_ms": latency["p99_ms"] <= 500,
    }

    per_minute = []
    for minute_index in sorted(minute_samples):
        values = [sample[0] for sample in minute_samples[minute_index]]
        minute_valid = sum(sample[1] for sample in minute_samples[minute_index])
        per_minute.append(
            {
                "minute": minute_index + 1,
                "samples": len(values),
                "valid_percent": round(minute_valid * 100 / len(values), 4),
                "p50_ms": percentile(values, 0.50),
                "p95_ms": percentile(values, 0.95),
                "p99_ms": percentile(values, 0.99),
                "max_ms": max(values),
            }
        )

    return {
        "sample_count": sample_count,
        "expected_samples": expected_samples,
        "sample_tolerance": tolerance_samples,
        # attempted_rpm counts every request the generator observed leaving the
        # client; completed_rpm counts only business-valid 2xx responses. Neither
        # is an edge-side counter of offered/admitted/rejected traffic, which
        # still has to be reconciled against API Gateway metrics by hand.
        "attempted_rpm": round(attempted_rpm, 4),
        "completed_rpm": round(completed_rpm, 4),
        "rpm_basis": "client-observed samples; not an edge-side offered/admitted counter",
        "valid_count": valid_count,
        "valid_percent": round(valid_percent, 4),
        "first_sample_at": utc_iso(first_timestamp),
        "last_sample_at": utc_iso(max(timestamps)),
        "observed_sample_span_seconds": round((max(timestamps) - first_timestamp) / 1000, 3),
        "latency": latency,
        "errors": dict(sorted(errors.items())),
        "criteria": criteria,
        "core_http_result": "PASS" if all(criteria.values()) else "FAIL",
        "per_minute": per_minute,
    }
def evidence_inventory(run_dir: Path) -> dict[str, Any]:
    k8s_dir = run_dir / "k8s"

    def line_count(path: Path) -> int:
        if not path.is_file() or path.is_symlink():
            return 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return sum(1 for line in handle if line.strip())

    return {
        "autoscaling_snapshots": line_count(k8s_dir / "autoscaling.jsonl"),
        "resource_usage_snapshots": line_count(k8s_dir / "resource-usage.jsonl"),
        "application_metric_snapshots": len(list((k8s_dir / "prometheus").glob("*.prom")))
        if (k8s_dir / "prometheus").is_dir()
        else 0,
        "managed_cloudwatch_metrics": (run_dir / "managed-cloudwatch-metrics.json").is_file(),
        "cloudwatch_graphs": len(list((run_dir / "cloudwatch-graphs").rglob("*.png")))
        if (run_dir / "cloudwatch-graphs").is_dir()
        else 0,
    }


def analyze(results_root: Path, run_id: str) -> tuple[dict[str, Any], Path]:
    if not SAFE_ID.fullmatch(run_id):
        raise EvidenceError("run-id contains unsupported characters")
    root = results_root.expanduser().resolve()
    run_dir = (root / run_id).resolve()
    if run_dir.parent != root or not run_dir.is_dir():
        raise EvidenceError("run-id does not identify a result directory")

    manifest = read_json_object(run_dir / "manifest.json")
    if manifest.get("run_id") != run_id:
        raise EvidenceError("manifest run_id does not match the selected directory")
    target_rpm = positive_int(manifest.get("target_rpm"), "target_rpm")
    measured_seconds = positive_int(
        manifest.get("measured_seconds"), "measured_seconds", maximum=86_400
    )
    runs = positive_int(manifest.get("runs"), "runs", maximum=100)

    run_summaries = []
    for run_number in range(1, runs + 1):
        run_dir_entry = run_dir / f"run-{run_number}"
        summary = summarize_jtl(
            run_dir_entry / "measured.jtl", target_rpm, measured_seconds
        )
        summary["run"] = run_number
        run_summaries.append(summary)

    core_pass = all(run["core_http_result"] == "PASS" for run in run_summaries)
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "run_id": run_id,
        "protocol": {
            "target_rpm": target_rpm,
            "measured_seconds": measured_seconds,
            "runs": runs,
            "percentile_method": "nearest-rank over raw request elapsed times",
        },
        "runs": run_summaries,
        "core_http_result": "PASS" if core_pass else "FAIL",
        "full_baseline_result": "NOT_EVALUATED",
        "evidence_inventory": evidence_inventory(run_dir),
        "manual_checks_required": [
            "absence of sustained CPU, memory, connection, and storage saturation",
            "HPA decision, additional Ready capacity, and simultaneous SLO recovery within 60 seconds",
            "PostgreSQL and Redis managed metrics for the same measurement windows",
            "load-generator CPU below 80 percent and absence of generator throttling",
            "reconciliation of attempted_rpm/completed_rpm against API Gateway "
            "Count, 4XXError, 5XXError and throttle metrics, because the JTL only "
            "observes traffic from the client side",
        ],
    }
    return report, run_dir


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        f"# Resultado técnico - {report['run_id']}",
        "",
        f"- Resultado HTTP central: **{report['core_http_result']}**",
        f"- Resultado integral del baseline: **{report['full_baseline_result']}**",
        "- Los percentiles usan nearest-rank sobre las latencias crudas; no se promedian percentiles.",
        "",
        "El resultado integral queda pendiente hasta revisar saturación, HPA, servicios administrados y generador.",
        "",
        "| Corrida | Muestras | RPM intentadas | RPM completadas | Válidas | p50 | p95 | p99 | Máx. | HTTP central |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for run in report["runs"]:
        latency = run["latency"]
        lines.append(
            "| {run} | {samples} | {rpm:.2f} | {completed:.2f} | {valid:.2f}% | {p50} ms | {p95} ms | "
            "{p99} ms | {maximum} ms | {result} |".format(
                run=run["run"],
                samples=run["sample_count"],
                rpm=run["attempted_rpm"],
                completed=run["completed_rpm"],
                valid=run["valid_percent"],
                p50=latency["p50_ms"],
                p95=latency["p95_ms"],
                p99=latency["p99_ms"],
                maximum=latency["max_ms"],
                result=run["core_http_result"],
            )
        )

    for run in report["runs"]:
        lines.extend(
            [
                "",
                f"## Corrida {run['run']} por minuto",
                "",
                "| Minuto | Muestras | Válidas | p50 | p95 | p99 | Máx. |",
                "|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for minute in run["per_minute"]:
            lines.append(
                "| {minute} | {samples} | {valid:.2f}% | {p50} ms | {p95} ms | "
                "{p99} ms | {maximum} ms |".format(
                    minute=minute["minute"],
                    samples=minute["samples"],
                    valid=minute["valid_percent"],
                    p50=minute["p50_ms"],
                    p95=minute["p95_ms"],
                    p99=minute["p99_ms"],
                    maximum=minute["max_ms"],
                )
            )

    inventory = report["evidence_inventory"]
    lines.extend(
        [
            "",
            "## Cobertura de evidencia complementaria",
            "",
            f"- Snapshots HPA/deploy/pod: {inventory['autoscaling_snapshots']}",
            f"- Snapshots de CPU/memoria: {inventory['resource_usage_snapshots']}",
            f"- Snapshots Prometheus de aplicación: {inventory['application_metric_snapshots']}",
            "- Métricas CloudWatch administradas: "
            + ("sí" if inventory["managed_cloudwatch_metrics"] else "no"),
            f"- Gráficas PNG de CloudWatch: {inventory['cloudwatch_graphs']}",
            "",
            "## Revisión manual pendiente",
            "",
        ]
    )
    lines.extend(f"- {check}" for check in report["manual_checks_required"])
    lines.append("")
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=False, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".analysis-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="solventa-exp1-analysis-") as temporary:
        results_root = Path(temporary)
        run_dir = results_root / "self-test"
        evidence_dir = run_dir / "run-1"
        evidence_dir.mkdir(parents=True)
        (run_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "run_id": "self-test",
                    "target_rpm": 60,
                    "measured_seconds": 10,
                    "runs": 1,
                }
            ),
            encoding="utf-8",
        )
        with (evidence_dir / "measured.jtl").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow(["timeStamp", "elapsed", "responseCode", "success"])
            for index in range(10):
                writer.writerow([1_700_000_000_000 + index * 1000, 10 + index, 200, "true"])
        report, _ = analyze(results_root, "self-test")
        if report["core_http_result"] != "PASS":
            raise EvidenceError("Analyzer self-test did not pass")
    print("Experiment 1 analyzer self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="Safe identifier under the results root")
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "load-tests" / "results",
    )
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()

    try:
        if arguments.self_test:
            run_self_test()
            return 0
        if arguments.run_id is None:
            parser.error("--run-id is required unless --self-test is used")
        report, run_dir = analyze(arguments.results_root, arguments.run_id)
        atomic_write(
            run_dir / "analysis.json",
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        )
        atomic_write(run_dir / "analysis.md", markdown_report(report))
    except EvidenceError as error:
        parser.exit(1, f"ERROR: {error}\n")

    print(f"Analysis written to {run_dir / 'analysis.json'} and {run_dir / 'analysis.md'}")
    print(f"Core HTTP result: {report['core_http_result']}; full baseline: NOT_EVALUATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
