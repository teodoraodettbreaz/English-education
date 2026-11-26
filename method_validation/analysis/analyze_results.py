from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from method_validation.analysis.stats_utils import (
    binary_confusion_metrics,
    bootstrap_ci,
    exact_mcnemar,
    holm_adjust,
    icc_a_k_bootstrap,
    krippendorff_alpha_nominal,
    newcombe_method10,
    paired_binary_table,
    paired_bootstrap_ci,
    percentile,
    sign_flip_permutation,
    wilson_interval,
)


ANALYSIS_VERSION = "pathlex-validation-analysis-1.0.0"
BOOTSTRAP_REPETITIONS = 10_000
PERMUTATION_REPETITIONS = 10_000
BOOTSTRAP_SEED = 2026112141
PERMUTATION_SEED = 2026112142
VERIFIER_BOOTSTRAP_SEED = 2026112143
ICC_BOOTSTRAP_SEED = 2026112144
METHOD_ORDER = ("GLOBAL-REPAIR", "MEAN-PATH", "PathLex-MINIMAX")
METHOD_LABELS = {
    "GLOBAL-REPAIR": "GLOBAL",
    "MEAN-PATH": "MEAN-PATH",
    "PathLex-MINIMAX": "PathLex",
}
METHOD_COLORS = {
    "GLOBAL-REPAIR": "#7B8794",
    "MEAN-PATH": "#2E6F95",
    "PathLex-MINIMAX": "#16826C",
}
CONTINUOUS_FIELDS = {
    "wpc": "gold_wpc",
    "path_pass_ratio": "gold_path_pass_ratio",
    "path_opportunity_gap": "gold_path_opportunity_gap",
    "post_branch_qualified_ratio": "post_branch_qualified_ratio",
    "oov_rate": "oov_rate",
    "repair_rounds": "repair_rounds",
    "candidate_evaluations": "candidate_evaluations",
    "node_count": "node_count",
}
NARRATIVE_DIMENSIONS = (
    "grammar_naturalness",
    "plot_coherence",
    "cefr_fit",
    "choice_consequence",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        ordered: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    ordered.append(key)
                    seen.add(key)
        fieldnames = ordered
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _bootstrap_mean(values: Sequence[float], seed_offset: int) -> tuple[float, float, float]:
    return bootstrap_ci(
        values,
        repetitions=BOOTSTRAP_REPETITIONS,
        seed=BOOTSTRAP_SEED + seed_offset,
    )


def analyze_methods(outputs: list[dict[str, Any]], results_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_method: dict[str, list[dict[str, Any]]] = {
        method: sorted(
            [row for row in outputs if row["method"] == method],
            key=lambda row: row["sample_id"],
        )
        for method in METHOD_ORDER
    }
    if any(len(rows) != 240 for rows in by_method.values()):
        raise RuntimeError("Each method must have exactly 240 specification-level outputs")
    method_rows: list[dict[str, Any]] = []
    method_summary: dict[str, Any] = {}
    for method_index, method in enumerate(METHOD_ORDER):
        rows = by_method[method]
        agp_count = sum(bool(row["agp"]) for row in rows)
        agp_rate = agp_count / len(rows)
        agp_low, agp_high = wilson_interval(agp_count, len(rows))
        status_counts = Counter(row["status"] for row in rows)
        summary: dict[str, Any] = {
            "n": len(rows),
            "agp_count": agp_count,
            "agp_rate": agp_rate,
            "agp_wilson_low": agp_low,
            "agp_wilson_high": agp_high,
            "status_counts": dict(status_counts),
        }
        flat_row: dict[str, Any] = {
            "method": method,
            "n": len(rows),
            "agp_count": agp_count,
            "agp_rate": agp_rate,
            "agp_wilson_low": agp_low,
            "agp_wilson_high": agp_high,
            "verified_count": status_counts.get("VERIFIED", 0),
            "counterexample_count": status_counts.get("COUNTEREXAMPLE", 0),
            "unknown_count": status_counts.get("UNKNOWN", 0),
        }
        for field_index, (metric_name, source_name) in enumerate(CONTINUOUS_FIELDS.items()):
            values = [float(row[source_name]) for row in rows]
            estimate, low, high = _bootstrap_mean(values, method_index * 20 + field_index)
            metric = {
                "mean": estimate,
                "bootstrap_low": low,
                "bootstrap_high": high,
            }
            summary[metric_name] = metric
            flat_row[f"{metric_name}_mean"] = estimate
            flat_row[f"{metric_name}_bootstrap_low"] = low
            flat_row[f"{metric_name}_bootstrap_high"] = high
        method_summary[method] = summary
        method_rows.append(flat_row)
    write_csv(results_dir / "method_metrics.csv", method_rows)

    pathlex = by_method["PathLex-MINIMAX"]
    mean_path = by_method["MEAN-PATH"]
    if [row["sample_id"] for row in pathlex] != [row["sample_id"] for row in mean_path]:
        raise RuntimeError("Paired method rows are not aligned")
    pathlex_agp = [bool(row["agp"]) for row in pathlex]
    mean_agp = [bool(row["agp"]) for row in mean_path]
    paired_table = paired_binary_table(pathlex_agp, mean_agp)
    rd, rd_low, rd_high = newcombe_method10(pathlex_agp, mean_agp)
    boot_rd, boot_low, boot_high = paired_bootstrap_ci(
        pathlex_agp,
        mean_agp,
        repetitions=BOOTSTRAP_REPETITIONS,
        seed=BOOTSTRAP_SEED + 100,
    )
    paired_agp_row = {
        "comparison": "PathLex-MINIMAX minus MEAN-PATH",
        **paired_table,
        "n": len(pathlex_agp),
        "risk_difference": rd,
        "newcombe10_low": rd_low,
        "newcombe10_high": rd_high,
        "exact_mcnemar_p": exact_mcnemar(pathlex_agp, mean_agp),
        "bootstrap_risk_difference": boot_rd,
        "bootstrap_low": boot_low,
        "bootstrap_high": boot_high,
    }
    write_csv(results_dir / "paired_agp.csv", [paired_agp_row])

    paired_continuous: list[dict[str, Any]] = []
    supportive_names = ("wpc", "path_pass_ratio", "path_opportunity_gap")
    raw_p_values: list[float] = []
    provisional: list[dict[str, Any]] = []
    for index, metric_name in enumerate(supportive_names):
        source = CONTINUOUS_FIELDS[metric_name]
        left = [float(row[source]) for row in pathlex]
        right = [float(row[source]) for row in mean_path]
        estimate, low, high = paired_bootstrap_ci(
            left,
            right,
            repetitions=BOOTSTRAP_REPETITIONS,
            seed=BOOTSTRAP_SEED + 120 + index,
        )
        permutation_estimate, p_value = sign_flip_permutation(
            left,
            right,
            repetitions=PERMUTATION_REPETITIONS,
            seed=PERMUTATION_SEED + index,
        )
        row = {
            "metric": metric_name,
            "comparison": "PathLex-MINIMAX minus MEAN-PATH",
            "paired_mean_difference": estimate,
            "bootstrap_low": low,
            "bootstrap_high": high,
            "permutation_mean_difference": permutation_estimate,
            "permutation_p_raw": p_value,
        }
        raw_p_values.append(p_value)
        provisional.append(row)
    adjusted = holm_adjust(raw_p_values)
    for row, adjusted_value in zip(provisional, adjusted):
        row["holm_adjusted_p"] = adjusted_value
        paired_continuous.append(row)
    write_csv(results_dir / "paired_continuous_metrics.csv", paired_continuous)

    comparison_summary = {
        "paired_agp": paired_agp_row,
        "paired_continuous": paired_continuous,
    }
    return {"methods": method_summary, "comparisons": comparison_summary}, method_rows


def analyze_strata(outputs: list[dict[str, Any]], results_dir: Path) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in outputs:
        grouped[(row["stratum"], row["method"])].append(row)
    rows: list[dict[str, Any]] = []
    for (stratum, method), items in sorted(grouped.items()):
        agp_count = sum(bool(item["agp"]) for item in items)
        low, high = wilson_interval(agp_count, len(items))
        rows.append(
            {
                "stratum": stratum,
                "method": method,
                "n": len(items),
                "agp_count": agp_count,
                "agp_rate": agp_count / len(items),
                "agp_wilson_low": low,
                "agp_wilson_high": high,
                "wpc_mean": fmean(float(item["gold_wpc"]) for item in items),
                "path_pass_ratio_mean": fmean(float(item["gold_path_pass_ratio"]) for item in items),
                "path_opportunity_gap_mean": fmean(float(item["gold_path_opportunity_gap"]) for item in items),
                "unknown_count": sum(item["status"] == "UNKNOWN" for item in items),
            }
        )
    write_csv(results_dir / "stratified_metrics.csv", rows)
    return rows


def _cluster_precision_interval(
    joined: Sequence[dict[str, Any]], seed: int
) -> tuple[float, float, float]:
    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in joined:
        by_cluster[row["sample_id"]].append(row)
    clusters = sorted(by_cluster)
    rng = random.Random(seed)

    def precision(rows: Iterable[dict[str, Any]]) -> float:
        tp = fp = 0
        for item in rows:
            predicted = item["prediction"] == "accepted"
            gold = item["gold_label"] == "qualified"
            tp += int(predicted and gold)
            fp += int(predicted and not gold)
        return tp / (tp + fp) if tp + fp else float("nan")

    observed = precision(joined)
    draws: list[float] = []
    for _ in range(BOOTSTRAP_REPETITIONS):
        sampled_rows: list[dict[str, Any]] = []
        for _cluster in clusters:
            selected = clusters[rng.randrange(len(clusters))]
            sampled_rows.extend(by_cluster[selected])
        value = precision(sampled_rows)
        if math.isfinite(value):
            draws.append(value)
    return observed, percentile(draws, 0.025), percentile(draws, 0.975)


def analyze_verifier(data_dir: Path, predictions_dir: Path, results_dir: Path) -> dict[str, Any]:
    gold_rows = load_jsonl(data_dir / "gold_opportunities.jsonl")
    prediction_rows = load_jsonl(predictions_dir / "verifier_predictions.jsonl")
    gold = {row["candidate_id"]: row for row in gold_rows}
    if set(gold) != {row["candidate_id"] for row in prediction_rows}:
        raise RuntimeError("Verifier predictions and adjudicated opportunities do not align")
    joined = [
        {
            **prediction,
            "gold_label": gold[prediction["candidate_id"]]["label"],
        }
        for prediction in prediction_rows
    ]
    strata: list[tuple[str, list[dict[str, Any]]]] = [("overall", joined)]
    strata.extend(
        (cefr, [row for row in joined if row["cefr_level"] == cefr])
        for cefr in ("A1", "B1", "B2")
    )
    metric_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for index, (label, rows) in enumerate(strata):
        gold_binary = [row["gold_label"] == "qualified" for row in rows]
        predicted_binary = [row["prediction"] == "accepted" for row in rows]
        metrics = binary_confusion_metrics(gold_binary, predicted_binary)
        precision, precision_low, precision_high = _cluster_precision_interval(
            rows, VERIFIER_BOOTSTRAP_SEED + index
        )
        abstentions = sum(row["prediction"] == "uncertain" for row in rows)
        metric_row = {
            "group": label,
            "n": len(rows),
            **metrics,
            "precision_cluster_bootstrap": precision,
            "precision_cluster_low": precision_low,
            "precision_cluster_high": precision_high,
            "abstention_count": abstentions,
            "abstention_rate": abstentions / len(rows),
            "coverage": 1.0 - abstentions / len(rows),
            "unresolved_gold_count": 0,
        }
        metric_rows.append(metric_row)
        summary[label] = metric_row
    write_csv(results_dir / "verifier_confusion_overall.csv", [metric_rows[0]])
    write_csv(results_dir / "verifier_confusion_by_cefr.csv", metric_rows[1:])
    return summary


def _category_pair_agreement(ratings: Sequence[Sequence[str]], category: str) -> float:
    agreements = opportunities = 0
    for row in ratings:
        for left_index in range(len(row)):
            for right_index in range(left_index + 1, len(row)):
                left, right = row[left_index], row[right_index]
                if category in {left, right}:
                    opportunities += 1
                    agreements += int(left == right == category)
    return agreements / opportunities if opportunities else float("nan")


def analyze_agreement(data_dir: Path, results_dir: Path) -> dict[str, Any]:
    rounds = [
        load_jsonl(data_dir / f"annotation_round_{index:02d}.jsonl")
        for index in range(1, 4)
    ]
    by_round = [
        {row["blind_item_id"]: row for row in round_rows}
        for round_rows in rounds
    ]
    item_ids = sorted(by_round[0])
    if any(set(mapping) != set(item_ids) for mapping in by_round[1:]):
        raise RuntimeError("Annotation rounds do not contain identical blinded items")
    ratings = [
        [mapping[item_id]["label"] for mapping in by_round]
        for item_id in item_ids
    ]
    complete_agreement = sum(len(set(row)) == 1 for row in ratings)
    adjudications = load_jsonl(data_dir / "adjudication.jsonl")
    adjudication_count = sum(bool(row["adjudication_required"]) for row in adjudications)
    disagreements = load_jsonl(data_dir / "annotation_disagreements.jsonl")
    metrics: dict[str, Any] = {
        "n_items": len(ratings),
        "n_rounds": 3,
        "krippendorff_alpha_nominal": krippendorff_alpha_nominal(ratings),
        "complete_agreement_count": complete_agreement,
        "complete_agreement_rate": complete_agreement / len(ratings),
        "disagreement_count": len(disagreements),
        "disagreement_rate": len(disagreements) / len(ratings),
        "adjudication_count": adjudication_count,
        "adjudication_rate": adjudication_count / len(ratings),
        "pair_agreement_qualified": _category_pair_agreement(ratings, "qualified"),
        "pair_agreement_unqualified": _category_pair_agreement(ratings, "unqualified"),
        "pair_agreement_uncertain": _category_pair_agreement(ratings, "uncertain"),
    }
    dump_json(results_dir / "agreement_metrics.json", metrics)
    return metrics


def analyze_narrative(data_dir: Path, results_dir: Path) -> dict[str, Any]:
    blind_rows = load_jsonl(data_dir / "narrative_blind_map.jsonl")
    blind = {row["output_id"]: row for row in blind_rows}
    rounds = [
        {row["output_id"]: row for row in load_jsonl(data_dir / f"narrative_rating_round_{index:02d}.jsonl")}
        for index in range(1, 4)
    ]
    if any(set(mapping) != set(blind) for mapping in rounds):
        raise RuntimeError("Narrative rating rounds do not align with the blind map")
    sample_ids = {row["sample_id"] for row in blind_rows}
    if len(sample_ids) != 96:
        raise RuntimeError(f"Narrative subset must contain 96 specifications, found {len(sample_ids)}")

    consensus: dict[tuple[str, str, str], dict[str, float]] = {}
    icc_summary: dict[str, Any] = {}
    for dimension_index, dimension in enumerate(NARRATIVE_DIMENSIONS):
        matrix: list[list[float]] = []
        for output_id in sorted(blind):
            scores = [float(round_map[output_id]["scores"][dimension]) for round_map in rounds]
            matrix.append(scores)
            mapping = blind[output_id]
            consensus.setdefault(
                (mapping["sample_id"], mapping["method"], mapping["path_kind"]), {}
            )[dimension] = fmean(scores)
        estimate, low, high = icc_a_k_bootstrap(
            matrix,
            repetitions=BOOTSTRAP_REPETITIONS,
            seed=ICC_BOOTSTRAP_SEED + dimension_index,
        )
        icc_summary[dimension] = {
            "icc_a_3": estimate,
            "bootstrap_low": low,
            "bootstrap_high": high,
            "n_outputs": len(matrix),
        }

    comparison_rows: list[dict[str, Any]] = []
    comparison_summary: dict[str, Any] = {"icc": icc_summary, "paths": {}}
    for path_index, path_kind in enumerate(("worst", "standard")):
        path_summary: dict[str, Any] = {}
        for dimension_index, dimension in enumerate(NARRATIVE_DIMENSIONS):
            ordered_ids = sorted(sample_ids)
            pathlex = [
                consensus[(sample_id, "PathLex-MINIMAX", path_kind)][dimension]
                for sample_id in ordered_ids
            ]
            mean_path = [
                consensus[(sample_id, "MEAN-PATH", path_kind)][dimension]
                for sample_id in ordered_ids
            ]
            estimate, low, high = paired_bootstrap_ci(
                pathlex,
                mean_path,
                repetitions=BOOTSTRAP_REPETITIONS,
                seed=BOOTSTRAP_SEED + 300 + path_index * 10 + dimension_index,
            )
            noninferiority = path_kind == "worst" and low > -0.30
            row = {
                "path_kind": path_kind,
                "dimension": dimension,
                "n_specifications": len(ordered_ids),
                "pathlex_mean": fmean(pathlex),
                "mean_path_mean": fmean(mean_path),
                "paired_difference": estimate,
                "bootstrap_low": low,
                "bootstrap_high": high,
                "one_sided_97_5_lower": low if path_kind == "worst" else "",
                "noninferiority_margin": -0.30 if path_kind == "worst" else "",
                "noninferiority_pass": noninferiority if path_kind == "worst" else "",
            }
            comparison_rows.append(row)
            path_summary[dimension] = row
        comparison_summary["paths"][path_kind] = path_summary
    write_csv(results_dir / "narrative_noninferiority.csv", comparison_rows)
    dump_json(results_dir / "narrative_reliability.json", icc_summary)
    return comparison_summary


def _iqr(values: Sequence[float]) -> float:
    ordered = sorted(values)
    return percentile(ordered, 0.75) - percentile(ordered, 0.25)


def analyze_stability(predictions_dir: Path, results_dir: Path) -> dict[str, Any]:
    rows = load_jsonl(predictions_dir / "seed_stability_outputs.jsonl")
    by_method_sample: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_method_sample[(row["method"], row["sample_id"])].append(row)
    methods = sorted({row["method"] for row in rows}, key=METHOD_ORDER.index)
    sample_ids = sorted({row["sample_id"] for row in rows})
    seed_values = sorted({int(row["seed_variant"]) for row in rows})
    if len(sample_ids) != 24 or seed_values != [0, 1, 2]:
        raise RuntimeError("Stability check requires 24 specifications and three seeds")
    result_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for method in methods:
        within_sd: list[float] = []
        consistent = 0
        for sample_id in sample_ids:
            items = sorted(
                by_method_sample[(method, sample_id)], key=lambda item: item["seed_variant"]
            )
            if len(items) != 3:
                raise RuntimeError("Each stability specification/method needs three runs")
            within_sd.append(statistics.pstdev(float(item["gold_wpc"]) for item in items))
            consistent += int(len({bool(item["agp"]) for item in items}) == 1)
        row = {
            "scope": method,
            "n_specifications": len(sample_ids),
            "n_seeds": len(seed_values),
            "mean_within_spec_wpc_sd": fmean(within_sd),
            "median_within_spec_wpc_sd": statistics.median(within_sd),
            "iqr_within_spec_wpc_sd": _iqr(within_sd),
            "agp_consistent_count": consistent,
            "agp_consistency_rate": consistent / len(sample_ids),
        }
        result_rows.append(row)
        summary[method] = row
    lookup = {
        (row["sample_id"], int(row["seed_variant"]), row["method"]): row
        for row in rows
    }
    stable_rank_count = 0
    for sample_id in sample_ids:
        rankings = []
        for seed in seed_values:
            rankings.append(
                tuple(
                    sorted(
                        methods,
                        key=lambda method: (
                            -float(lookup[(sample_id, seed, method)]["gold_wpc"]),
                            method,
                        ),
                    )
                )
            )
        stable_rank_count += int(len(set(rankings)) == 1)
    overall = {
        "scope": "method_ranking",
        "n_specifications": len(sample_ids),
        "n_seeds": len(seed_values),
        "ranking_stable_count": stable_rank_count,
        "ranking_stability_rate": stable_rank_count / len(sample_ids),
    }
    result_rows.append(overall)
    summary["method_ranking"] = overall
    write_csv(results_dir / "seed_stability.csv", result_rows)
    return summary


def analyze_sentinels(
    main_outputs: list[dict[str, Any]], predictions_dir: Path, results_dir: Path
) -> dict[str, Any]:
    sentinels = load_jsonl(predictions_dir / "sentinel_outputs.jsonl")
    accepted = sum(bool(row["certificate_accepted"]) for row in sentinels)
    unknown = sum(row["reported_disposition"] == "UNKNOWN" for row in sentinels)
    erroneous_feasible = sum(
        row["reported_disposition"] == "PLAN-FEASIBLE" for row in sentinels
    )
    false_unsat_samples = {
        row["sample_id"]
        for row in main_outputs
        if row["status"] == "PLAN-INFEASIBLE(UNSAT)"
    }
    feasible_unknown_samples = {
        row["sample_id"] for row in main_outputs if row["status"] == "UNKNOWN"
    }
    summary = {
        "sentinel_n": len(sentinels),
        "accepted_unsat_certificates": accepted,
        "sentinel_unknown": unknown,
        "sentinel_erroneous_feasible": erroneous_feasible,
        "sentinel_certificate_sensitivity": accepted / len(sentinels),
        "feasible_n": len({row["sample_id"] for row in main_outputs}),
        "false_unsat_count": len(false_unsat_samples),
        "feasible_unknown_count": len(feasible_unknown_samples),
    }
    detail_rows: list[dict[str, Any]] = [
        {
            "scope": "sentinel_total",
            **summary,
        }
    ]
    for sentinel_type in sorted({row["sentinel_type"] for row in sentinels}):
        items = [row for row in sentinels if row["sentinel_type"] == sentinel_type]
        detail_rows.append(
            {
                "scope": sentinel_type,
                "sentinel_n": len(items),
                "accepted_unsat_certificates": sum(
                    bool(row["certificate_accepted"]) for row in items
                ),
                "sentinel_unknown": sum(
                    row["reported_disposition"] == "UNKNOWN" for row in items
                ),
                "sentinel_erroneous_feasible": sum(
                    row["reported_disposition"] == "PLAN-FEASIBLE" for row in items
                ),
            }
        )
    write_csv(results_dir / "sentinel_diagnostics.csv", detail_rows)
    return summary


def _style_axes(ax: Any) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#D7DEE3", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)


def plot_method_comparison(method_summary: dict[str, Any], results_dir: Path) -> None:
    methods = list(METHOD_ORDER)
    x = list(range(len(methods)))
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
    rates = [method_summary[method]["agp_rate"] for method in methods]
    lows = [method_summary[method]["agp_wilson_low"] for method in methods]
    highs = [method_summary[method]["agp_wilson_high"] for method in methods]
    axes[0].bar(x, rates, color=[METHOD_COLORS[method] for method in methods], width=0.68)
    axes[0].errorbar(
        x,
        rates,
        yerr=[[rate - low for rate, low in zip(rates, lows)], [high - rate for rate, high in zip(rates, highs)]],
        fmt="none",
        ecolor="#1A2B34",
        capsize=4,
        linewidth=1.2,
    )
    axes[0].set_xticks(x, [METHOD_LABELS[method] for method in methods], rotation=12)
    axes[0].set_ylim(0, 1)
    axes[0].set_ylabel("All-path graph pass rate")
    axes[0].set_title("AGP (Wilson 95% CI)")
    for index, value in enumerate(rates):
        axes[0].text(index, value + 0.035, f"{value:.1%}", ha="center", fontsize=9)
    _style_axes(axes[0])

    wpc = [method_summary[method]["wpc"]["mean"] for method in methods]
    wpc_low = [method_summary[method]["wpc"]["bootstrap_low"] for method in methods]
    wpc_high = [method_summary[method]["wpc"]["bootstrap_high"] for method in methods]
    axes[1].bar(x, wpc, color=[METHOD_COLORS[method] for method in methods], width=0.68)
    axes[1].errorbar(
        x,
        wpc,
        yerr=[[value - low for value, low in zip(wpc, wpc_low)], [high - value for value, high in zip(wpc, wpc_high)]],
        fmt="none",
        ecolor="#1A2B34",
        capsize=4,
        linewidth=1.2,
    )
    axes[1].set_xticks(x, [METHOD_LABELS[method] for method in methods], rotation=12)
    axes[1].set_ylim(0.75, 1.0)
    axes[1].set_ylabel("Worst-path qualified coverage")
    axes[1].set_title("WPC (specification bootstrap 95% CI)")
    for index, value in enumerate(wpc):
        axes[1].text(index, value + 0.008, f"{value:.3f}", ha="center", fontsize=9)
    _style_axes(axes[1])
    fig.savefig(results_dir / "method_agp_wpc.png", dpi=180)
    plt.close(fig)


def plot_paired_agp(paired: dict[str, Any], results_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.8), constrained_layout=True)
    labels = ["PathLex only", "MEAN only"]
    values = [paired["first_only"], paired["second_only"]]
    axes[0].bar(labels, values, color=[METHOD_COLORS["PathLex-MINIMAX"], METHOD_COLORS["MEAN-PATH"]], width=0.58)
    axes[0].set_ylabel("Discordant specifications")
    axes[0].set_title("Paired AGP discordance")
    for index, value in enumerate(values):
        axes[0].text(index, value + 1.0, str(value), ha="center")
    _style_axes(axes[0])
    rd = paired["risk_difference"]
    low, high = paired["newcombe10_low"], paired["newcombe10_high"]
    axes[1].axvline(0, color="#8C969D", linestyle="--", linewidth=1)
    axes[1].errorbar(
        [rd],
        [0],
        xerr=[[rd - low], [high - rd]],
        fmt="o",
        color=METHOD_COLORS["PathLex-MINIMAX"],
        capsize=5,
        markersize=7,
    )
    axes[1].set_yticks([0], ["PathLex − MEAN"])
    axes[1].set_xlabel("Paired risk difference")
    axes[1].set_title("Newcombe method-10 95% CI")
    axes[1].set_xlim(min(-0.03, low - 0.03), max(0.30, high + 0.03))
    axes[1].grid(axis="x", color="#D7DEE3", linewidth=0.7)
    axes[1].spines["top"].set_visible(False)
    axes[1].spines["right"].set_visible(False)
    fig.savefig(results_dir / "paired_agp_difference.png", dpi=180)
    plt.close(fig)


def plot_confusion(verifier: dict[str, Any], results_dir: Path) -> None:
    overall = verifier["overall"]
    matrix = [[overall["tn"], overall["fp"]], [overall["fn"], overall["tp"]]]
    fig, ax = plt.subplots(figsize=(5.1, 4.5), constrained_layout=True)
    image = ax.imshow(matrix, cmap="Blues")
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            color = "white" if value > max(max(item) for item in matrix) * 0.55 else "#142B3A"
            ax.text(column_index, row_index, f"{value:,}", ha="center", va="center", color=color, fontsize=13)
    ax.set_xticks([0, 1], ["Predicted reject", "Predicted accept"])
    ax.set_yticks([0, 1], ["Gold unqualified", "Gold qualified"])
    ax.set_title("Internal verifier confusion matrix")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.savefig(results_dir / "verifier_confusion_matrix.png", dpi=180)
    plt.close(fig)


def plot_narrative(narrative: dict[str, Any], results_dir: Path) -> None:
    rows = [narrative["paths"]["worst"][dimension] for dimension in NARRATIVE_DIMENSIONS]
    estimates = [float(row["paired_difference"]) for row in rows]
    lows = [float(row["bootstrap_low"]) for row in rows]
    highs = [float(row["bootstrap_high"]) for row in rows]
    y = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    ax.axvline(-0.30, color="#A8345B", linestyle="--", linewidth=1.4, label="Non-inferiority margin")
    ax.axvline(0, color="#8C969D", linestyle=":", linewidth=1)
    ax.errorbar(
        estimates,
        y,
        xerr=[[estimate - low for estimate, low in zip(estimates, lows)], [high - estimate for estimate, high in zip(estimates, highs)]],
        fmt="o",
        color=METHOD_COLORS["PathLex-MINIMAX"],
        ecolor=METHOD_COLORS["PathLex-MINIMAX"],
        capsize=4,
        markersize=7,
    )
    ax.set_yticks(y, [item.replace("_", " ") for item in NARRATIVE_DIMENSIONS])
    ax.set_xlabel("PathLex − MEAN-PATH score (5-point scale)")
    ax.set_title("Worst-path narrative quality: paired bootstrap interval")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="x", color="#D7DEE3", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.savefig(results_dir / "narrative_noninferiority.png", dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description='Analyze the PathLex comparison and write the result files.')
    parser.add_argument(
        "--validation-root",
        type=Path,
        default=ROOT / "method_validation",
        help="Method-validation artifact root.",
    )
    args = parser.parse_args()
    validation_root = args.validation_root.resolve()
    data_dir = validation_root / "data"
    predictions_dir = validation_root / "predictions"
    results_dir = validation_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    outputs = load_jsonl(predictions_dir / "all_method_outputs.jsonl")
    method_analysis, _method_rows = analyze_methods(outputs, results_dir)
    stratified = analyze_strata(outputs, results_dir)
    verifier = analyze_verifier(data_dir, predictions_dir, results_dir)
    agreement = analyze_agreement(data_dir, results_dir)
    narrative = analyze_narrative(data_dir, results_dir)
    stability = analyze_stability(predictions_dir, results_dir)
    sentinels = analyze_sentinels(outputs, predictions_dir, results_dir)

    summary = {
        "analysis_version": ANALYSIS_VERSION,
        "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
        "permutation_repetitions": PERMUTATION_REPETITIONS,
        "seeds": {
            "bootstrap": BOOTSTRAP_SEED,
            "permutation": PERMUTATION_SEED,
            "verifier_cluster_bootstrap": VERIFIER_BOOTSTRAP_SEED,
            "icc_bootstrap": ICC_BOOTSTRAP_SEED,
        },
        **method_analysis,
        "stratified_metrics": stratified,
        "verifier": verifier,
        "annotation_agreement": agreement,
        "narrative": narrative,
        "stability": stability,
        "sentinels": sentinels,
        "decision_gates": {
            "agp_superiority": (
                method_analysis["comparisons"]["paired_agp"]["newcombe10_low"] > 0
            ),
            "wpc_direction_consistent": (
                next(
                    row
                    for row in method_analysis["comparisons"]["paired_continuous"]
                    if row["metric"] == "wpc"
                )["paired_mean_difference"]
                > 0
            ),
            "narrative_all_dimensions_noninferior": all(
                narrative["paths"]["worst"][dimension]["noninferiority_pass"]
                for dimension in NARRATIVE_DIMENSIONS
            ),
            "verifier_macro_f1": verifier["overall"]["macro_f1"] >= 0.85,
            "verifier_each_cefr_f1": all(
                verifier[cefr]["macro_f1"] >= 0.75 for cefr in ("A1", "B1", "B2")
            ),
            "verifier_precision_point": verifier["overall"]["precision"] >= 0.95,
            "verifier_precision_lower": verifier["overall"]["precision_cluster_low"] >= 0.90,
            "budget_gate": all(bool(row["budget_within"]) for row in outputs),
        },
    }
    dump_json(results_dir / "analysis_summary.json", summary)
    plot_method_comparison(method_analysis["methods"], results_dir)
    plot_paired_agp(method_analysis["comparisons"]["paired_agp"], results_dir)
    plot_confusion(verifier, results_dir)
    plot_narrative(narrative, results_dir)

    concise = {
        "agp": {
            method: {
                "count": method_analysis["methods"][method]["agp_count"],
                "rate": method_analysis["methods"][method]["agp_rate"],
            }
            for method in METHOD_ORDER
        },
        "paired_agp": method_analysis["comparisons"]["paired_agp"],
        "verifier_overall": verifier["overall"],
        "agreement": agreement,
        "narrative_worst": narrative["paths"]["worst"],
        "decision_gates": summary["decision_gates"],
    }
    print(json.dumps(concise, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
