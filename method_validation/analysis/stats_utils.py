from __future__ import annotations

import math
import random
from collections import Counter
from statistics import NormalDist, fmean
from typing import Callable, Hashable, Iterable, Sequence


Number = int | float


def percentile(values: Sequence[Number], q: float) -> float:


    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be between 0 and 1")
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("percentile requires at least one value")
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def wilson_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> tuple[float, float]:


    if total <= 0:
        raise ValueError("total must be positive")
    if not 0 <= successes <= total:
        raise ValueError("successes must lie between zero and total")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    observed = successes / total
    z2_over_n = z * z / total
    denominator = 1.0 + z2_over_n
    centre = (observed + z2_over_n / 2.0) / denominator
    half_width = (
        z
        * math.sqrt(
            observed * (1.0 - observed) / total
            + (z * z) / (4.0 * total * total)
        )
        / denominator
    )
    return max(0.0, centre - half_width), min(1.0, centre + half_width)


def paired_binary_table(
    first: Sequence[bool | int],
    second: Sequence[bool | int],
) -> dict[str, int]:


    if len(first) != len(second) or not first:
        raise ValueError("paired sequences must have the same non-zero length")
    table = {"both": 0, "first_only": 0, "second_only": 0, "neither": 0}
    for left, right in zip(first, second):
        left_bool, right_bool = bool(left), bool(right)
        if left_bool and right_bool:
            table["both"] += 1
        elif left_bool:
            table["first_only"] += 1
        elif right_bool:
            table["second_only"] += 1
        else:
            table["neither"] += 1
    return table


def _paired_cell_proportions(
    first: Sequence[bool | int], second: Sequence[bool | int]
) -> tuple[dict[str, int], dict[str, float]]:
    table = paired_binary_table(first, second)
    total = len(first)
    proportions = {key: value / total for key, value in table.items()}
    return table, proportions


def newcombe_method10(
    first: Sequence[bool | int],
    second: Sequence[bool | int],
    confidence: float = 0.95,
) -> tuple[float, float, float]:


    table, cells = _paired_cell_proportions(first, second)
    total = len(first)
    first_successes = table["both"] + table["first_only"]
    second_successes = table["both"] + table["second_only"]
    p_first = first_successes / total
    p_second = second_successes / total
    difference = p_first - p_second
    first_low, first_high = wilson_interval(first_successes, total, confidence)
    second_low, second_high = wilson_interval(second_successes, total, confidence)

    denominator = math.sqrt(
        p_first * (1.0 - p_first) * p_second * (1.0 - p_second)
    )
    if denominator == 0.0:
        correlation = 0.0
    else:
        correlation = (
            cells["both"] * cells["neither"]
            - cells["first_only"] * cells["second_only"]
        ) / denominator
        correlation = max(-1.0, min(1.0, correlation))

    lower_variance = (
        (p_first - first_low) ** 2
        + (second_high - p_second) ** 2
        - 2.0
        * correlation
        * (p_first - first_low)
        * (second_high - p_second)
    )
    upper_variance = (
        (first_high - p_first) ** 2
        + (p_second - second_low) ** 2
        - 2.0
        * correlation
        * (first_high - p_first)
        * (p_second - second_low)
    )
    lower = difference - math.sqrt(max(0.0, lower_variance))
    upper = difference + math.sqrt(max(0.0, upper_variance))
    return difference, max(-1.0, lower), min(1.0, upper)


def exact_mcnemar(
    first: Sequence[bool | int], second: Sequence[bool | int]
) -> float:


    table = paired_binary_table(first, second)
    discordant = table["first_only"] + table["second_only"]
    if discordant == 0:
        return 1.0
    smaller = min(table["first_only"], table["second_only"])
    lower_tail = sum(math.comb(discordant, index) for index in range(smaller + 1))
    return min(1.0, 2.0 * lower_tail / (2**discordant))


def _bootstrap_indices(
    sample_size: int,
    rng: random.Random,
    cluster_ids: Sequence[Hashable] | None,
) -> list[int]:
    if cluster_ids is None:
        return [rng.randrange(sample_size) for _ in range(sample_size)]
    if len(cluster_ids) != sample_size:
        raise ValueError("cluster_ids must match the number of observations")
    members: dict[Hashable, list[int]] = {}
    for index, cluster in enumerate(cluster_ids):
        members.setdefault(cluster, []).append(index)
    clusters = list(members)
    if not clusters:
        raise ValueError("cluster_ids cannot be empty")
    sampled: list[int] = []
    for _ in clusters:
        selected = clusters[rng.randrange(len(clusters))]
        sampled.extend(members[selected])
    return sampled


def bootstrap_ci(
    values: Sequence[Number],
    *,
    statistic: Callable[[Sequence[float]], float] | None = None,
    repetitions: int = 10_000,
    seed: int = 20261121,
    confidence: float = 0.95,
    cluster_ids: Sequence[Hashable] | None = None,
) -> tuple[float, float, float]:


    observed_values = [float(value) for value in values]
    if not observed_values:
        raise ValueError("bootstrap requires at least one observation")
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    function = statistic or fmean
    estimate = float(function(observed_values))
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(repetitions):
        indices = _bootstrap_indices(len(observed_values), rng, cluster_ids)
        draws.append(float(function([observed_values[index] for index in indices])))
    alpha = 1.0 - confidence
    return estimate, percentile(draws, alpha / 2.0), percentile(draws, 1.0 - alpha / 2.0)


def paired_bootstrap_ci(
    first: Sequence[Number],
    second: Sequence[Number],
    *,
    statistic: Callable[[Sequence[float]], float] | None = None,
    repetitions: int = 10_000,
    seed: int = 20261121,
    confidence: float = 0.95,
    cluster_ids: Sequence[Hashable] | None = None,
) -> tuple[float, float, float]:


    if len(first) != len(second) or not first:
        raise ValueError("paired sequences must have the same non-zero length")
    differences = [float(left) - float(right) for left, right in zip(first, second)]
    return bootstrap_ci(
        differences,
        statistic=statistic,
        repetitions=repetitions,
        seed=seed,
        confidence=confidence,
        cluster_ids=cluster_ids,
    )


def sign_flip_permutation(
    first: Sequence[Number],
    second: Sequence[Number] | None = None,
    *,
    repetitions: int = 10_000,
    seed: int = 20261121,
) -> tuple[float, float]:


    if second is None:
        differences = [float(value) for value in first]
    else:
        if len(first) != len(second):
            raise ValueError("paired sequences must have the same length")
        differences = [float(left) - float(right) for left, right in zip(first, second)]
    if not differences:
        raise ValueError("permutation test requires at least one pair")
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    observed = fmean(differences)
    rng = random.Random(seed)
    extreme = 0
    tolerance = 1e-15
    for _ in range(repetitions):
        permuted = fmean(
            value if rng.random() < 0.5 else -value for value in differences
        )
        if abs(permuted) + tolerance >= abs(observed):
            extreme += 1
    return observed, (extreme + 1.0) / (repetitions + 1.0)


def holm_adjust(p_values: Sequence[Number]) -> list[float]:


    if not p_values:
        return []
    values = [float(value) for value in p_values]
    if any(value < 0.0 or value > 1.0 for value in values):
        raise ValueError("p-values must lie between 0 and 1")
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [0.0] * len(values)
    running = 0.0
    total = len(values)
    for rank, original_index in enumerate(order):
        candidate = min(1.0, (total - rank) * values[original_index])
        running = max(running, candidate)
        adjusted[original_index] = running
    return adjusted


def krippendorff_alpha_nominal(
    ratings: Sequence[Sequence[Hashable | None]],
) -> float:


    observed_disagreements = 0
    observed_pairs = 0
    pooled: Counter[Hashable] = Counter()
    for row in ratings:
        valid = [label for label in row if label is not None]
        pooled.update(valid)
        if len(valid) < 2:
            continue
        for left_index, left in enumerate(valid):
            for right_index, right in enumerate(valid):
                if left_index == right_index:
                    continue
                observed_pairs += 1
                observed_disagreements += int(left != right)
    if observed_pairs == 0:
        raise ValueError("alpha requires at least one item with two ratings")
    total_ratings = sum(pooled.values())
    if total_ratings < 2:
        raise ValueError("alpha requires at least two ratings")
    observed = observed_disagreements / observed_pairs
    expected_agreement = sum(
        count * (count - 1) for count in pooled.values()
    ) / (total_ratings * (total_ratings - 1))
    expected = 1.0 - expected_agreement
    if expected == 0.0:
        return 1.0 if observed == 0.0 else float("nan")
    return 1.0 - observed / expected


def _complete_numeric_matrix(
    ratings: Sequence[Sequence[Number | None]],
) -> list[list[float]]:
    rows = [[float(value) for value in row] for row in ratings if all(value is not None for value in row)]
    if len(rows) < 2:
        raise ValueError("ICC requires at least two complete subjects")
    rater_counts = {len(row) for row in rows}
    if len(rater_counts) != 1 or next(iter(rater_counts)) < 2:
        raise ValueError("ICC requires a rectangular matrix with at least two raters")
    return rows


def icc_a_k(ratings: Sequence[Sequence[Number | None]]) -> float:


    matrix = _complete_numeric_matrix(ratings)
    subjects = len(matrix)
    raters = len(matrix[0])
    grand = fmean(value for row in matrix for value in row)
    subject_means = [fmean(row) for row in matrix]
    rater_means = [fmean(matrix[index][rater] for index in range(subjects)) for rater in range(raters)]
    ss_subject = raters * sum((mean - grand) ** 2 for mean in subject_means)
    ss_rater = subjects * sum((mean - grand) ** 2 for mean in rater_means)
    ss_total = sum((value - grand) ** 2 for row in matrix for value in row)
    ss_error = max(0.0, ss_total - ss_subject - ss_rater)
    ms_subject = ss_subject / (subjects - 1)
    ms_rater = ss_rater / (raters - 1)
    ms_error = ss_error / ((subjects - 1) * (raters - 1))
    denominator = ms_subject + (ms_rater - ms_error) / subjects
    if denominator == 0.0:
        return float("nan")
    return (ms_subject - ms_error) / denominator


def icc_a_k_bootstrap(
    ratings: Sequence[Sequence[Number | None]],
    *,
    repetitions: int = 10_000,
    seed: int = 20261121,
    confidence: float = 0.95,
) -> tuple[float, float, float]:


    matrix = _complete_numeric_matrix(ratings)
    estimate = icc_a_k(matrix)
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(repetitions):
        sample = [matrix[rng.randrange(len(matrix))] for _ in matrix]
        value = icc_a_k(sample)
        if math.isfinite(value):
            draws.append(value)
    if not draws:
        raise ValueError("all bootstrap ICC replicates were undefined")
    alpha = 1.0 - confidence
    return estimate, percentile(draws, alpha / 2.0), percentile(draws, 1.0 - alpha / 2.0)


def binary_confusion_metrics(
    gold: Sequence[bool | int], predictions: Sequence[bool | int]
) -> dict[str, float | int]:


    if len(gold) != len(predictions) or not gold:
        raise ValueError("gold and predictions must have the same non-zero length")
    tp = fp = fn = tn = 0
    for truth, prediction in zip(gold, predictions):
        truth_bool, prediction_bool = bool(truth), bool(prediction)
        if truth_bool and prediction_bool:
            tp += 1
        elif not truth_bool and prediction_bool:
            fp += 1
        elif truth_bool:
            fn += 1
        else:
            tn += 1

    def ratio(numerator: Number, denominator: Number) -> float:
        return float(numerator / denominator) if denominator else float("nan")

    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    specificity = ratio(tn, tn + fp)
    negative_predictive_value = ratio(tn, tn + fn)
    positive_f1 = ratio(2 * tp, 2 * tp + fp + fn)
    negative_f1 = ratio(2 * tn, 2 * tn + fp + fn)
    macro_f1 = fmean([positive_f1, negative_f1])
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "accuracy": ratio(tp + tn, len(gold)),
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "negative_predictive_value": negative_predictive_value,
        "positive_f1": positive_f1,
        "negative_f1": negative_f1,
        "macro_f1": macro_f1,
        "false_accept_rate": ratio(fp, fp + tn),
        "false_reject_rate": ratio(fn, fn + tp),
    }


def _self_test() -> None:
    assert percentile([0, 10], 0.25) == 2.5
    low, high = wilson_interval(50, 100)
    assert low < 0.5 < high
    first = [1, 1, 1, 0, 0, 0]
    second = [1, 0, 0, 1, 0, 0]
    assert paired_binary_table(first, second) == {
        "both": 1,
        "first_only": 2,
        "second_only": 1,
        "neither": 2,
    }
    difference, lower, upper = newcombe_method10(first, second)
    assert lower <= difference <= upper
    assert 0.0 <= exact_mcnemar(first, second) <= 1.0
    assert holm_adjust([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]
    assert krippendorff_alpha_nominal([["a", "a", "a"], ["b", "b", "a"]]) < 1.0
    assert math.isfinite(icc_a_k([[1, 1, 2], [2, 2, 2], [4, 5, 4]]))
    metrics = binary_confusion_metrics([1, 1, 0, 0], [1, 0, 1, 0])
    assert metrics["tp"] == metrics["fp"] == metrics["fn"] == metrics["tn"] == 1


if __name__ == "__main__":
    _self_test()
    print("stats_utils self-test passed")
