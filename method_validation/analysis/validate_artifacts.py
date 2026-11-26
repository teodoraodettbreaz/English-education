from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MV = ROOT / "method_validation"
METHODS = {"GLOBAL-REPAIR", "MEAN-PATH", "PathLex-MINIMAX"}


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    feasible = jsonl(MV / "data" / "final_test_specs.jsonl")
    sentinels = jsonl(MV / "data" / "sentinel_specs.jsonl")
    require(len(feasible) == 240, "final test set must contain 240 feasible specifications")
    require(len(sentinels) == 24, "sentinel set must contain 24 specifications")
    require(len({row["sample_id"] for row in feasible + sentinels}) == 264, "sample IDs must be unique")
    cells = Counter(row["stratum"] for row in feasible)
    require(len(cells) == 12 and set(cells.values()) == {20}, "the 12-cell test design is incomplete")

    outputs = jsonl(MV / "predictions" / "all_method_outputs.jsonl")
    require(len(outputs) == 720, "three methods must each produce 240 outputs")
    by_method = {method: [row for row in outputs if row["method"] == method] for method in METHODS}
    expected_ids = {row["sample_id"] for row in feasible}
    for method, rows in by_method.items():
        require(len(rows) == 240, f"{method} output count is not 240")
        require({row["sample_id"] for row in rows} == expected_ids, f"{method} used a different test set")
        require(all(row["budget_within"] for row in rows), f"{method} exceeded the frozen repair budget")

    expected_agp = {"GLOBAL-REPAIR": 108, "MEAN-PATH": 150, "PathLex-MINIMAX": 198}
    observed_agp = {method: sum(bool(row["agp"]) for row in rows) for method, rows in by_method.items()}
    require(observed_agp == expected_agp, f"AGP totals changed: {observed_agp}")

    gold = jsonl(MV / "data" / "gold_opportunities.jsonl")
    verifier = jsonl(MV / "predictions" / "verifier_predictions.jsonl")
    require(len(gold) == len(verifier) == 2898, "opportunity reference/prediction counts differ")
    require({row["candidate_id"] for row in gold} == {row["candidate_id"] for row in verifier}, "opportunity IDs differ")

    summary = json.loads((MV / "results" / "analysis_summary.json").read_text(encoding="utf-8"))
    require(all(summary["decision_gates"].values()), "one or more frozen decision gates failed")
    require(summary["comparisons"]["paired_agp"]["risk_difference"] > 0, "paired AGP advantage is absent")
    require(summary["verifier"]["overall"]["precision"] < 1.0, "verifier precision must retain observed errors")

    required_results = {
        "method_metrics.csv",
        "paired_agp.csv",
        "paired_continuous_metrics.csv",
        "verifier_confusion_overall.csv",
        "verifier_confusion_by_cefr.csv",
        "narrative_noninferiority.csv",
        "seed_stability.csv",
        "sentinel_diagnostics.csv",
        "method_agp_wpc.png",
        "paired_agp_difference.png",
        "verifier_confusion_matrix.png",
        "narrative_noninferiority.png",
    }
    for name in required_results:
        path = MV / "results" / name
        require(path.exists() and path.stat().st_size > 0, f"missing or empty result: {name}")

    print("method-validation artifact integrity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
