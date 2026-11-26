from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
VALIDATION_ROOT = ROOT / "method_validation"
MANIFEST = VALIDATION_ROOT / "data" / "freeze_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def line_count(path: Path) -> int | None:
    if path.suffix not in {".jsonl", ".csv", ".txt", ".md", ".py"}:
        return None
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def main() -> int:
    files: list[Path] = []
    for directory in ("data", "predictions", "analysis", "results"):
        base = VALIDATION_ROOT / directory
        if not base.exists():
            continue
        files.extend(
            path
            for path in base.rglob("*")
            if path.is_file()
            and path != MANIFEST
            and "__pycache__" not in path.parts
            and not path.name.endswith(".tmp")
        )
    report = ROOT / "method_validation.md"
    if report.exists():
        files.append(report)
    entries = []
    for path in sorted(set(files)):
        relative = path.relative_to(ROOT).as_posix()
        entries.append(
            {
                "path": relative,
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "lines": line_count(path),
            }
        )
    run_config_path = VALIDATION_ROOT / "predictions" / "run_config.json"
    run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
    payload = {
        "manifest_version": "pathlex-freeze-manifest-1.0.0",
        "frozen_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "workspace_python": sys.version.split()[0],
        "runner_version": run_config["runner_version"],
        "pathlex_version": run_config["pathlex_version"],
        "reference_version": run_config["reference_version"],
        "verifier_version": run_config["verifier_version"],
        "seeds": {
            "main": run_config["main_seed"],
            "annotation": run_config["annotation_seeds"],
            "verifier": run_config["verifier_seed"],
            "narrative": run_config["narrative_seeds"],
            "analysis": 2026112141,
        },
        "frozen_counts": {
            "feasible_test_specifications": run_config["test_specifications"],
            "boundary_sentinels": run_config["sentinels"],
            "candidate_opportunities": run_config["candidate_opportunities"],
            "method_outputs": run_config["method_outputs"],
        },
        "files": entries,
    }
    temporary = MANIFEST.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(MANIFEST)
    print(f"froze {len(entries)} files in {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
