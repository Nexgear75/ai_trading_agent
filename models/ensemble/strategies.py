"""Ensemble voting strategies.

Each strategy takes a list of Prediction objects (one per agent) and returns
a single aggregated Prediction. All strategies treat ``raw_value`` as a
continuous predicted return % and ``signal`` as the discretized direction.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from models.base_predictor import Prediction

AVAILABLE_STRATEGIES = ("majority_vote", "weighted_average", "confidence_weighted", "unanimous")


def majority_vote(predictions: Sequence[Prediction]) -> Prediction:
    """Simple majority vote on signal direction.

    Ties (e.g. 1 buy, 1 sell) or outright hold majorities resolve to hold.
    raw_value is the mean of all agents' predictions.
    """
    counts: dict[str, int] = {"buy": 0, "sell": 0, "hold": 0}
    for p in predictions:
        counts[p.signal] += 1

    max_votes = max(counts.values())
    winners = [s for s, v in counts.items() if v == max_votes]

    # Tie or hold wins → hold
    if len(winners) > 1 or winners[0] == "hold":
        signal = "hold"
    else:
        signal = winners[0]

    matching = [p for p in predictions if p.signal == signal]
    confidence = float(np.mean([p.confidence for p in matching])) if matching else 0.0
    raw_value = float(np.mean([p.raw_value for p in predictions]))
    return Prediction(signal=signal, confidence=confidence, raw_value=raw_value)


def weighted_average(
    predictions: Sequence[Prediction],
    weights: Sequence[float],
    threshold: float,
) -> Prediction:
    """Weighted average of raw return predictions, then apply threshold.

    Higher-weighted models have more influence on the final direction.
    """
    w = np.array(weights, dtype=float)
    w /= w.sum()
    raw_values = np.array([p.raw_value for p in predictions])
    avg_pred = float(np.dot(w, raw_values))

    confidence = min(1.0, abs(avg_pred) / max(threshold * 2, 1e-9))

    if avg_pred > threshold:
        signal = "buy"
    elif avg_pred < -threshold:
        signal = "sell"
    else:
        signal = "hold"

    return Prediction(signal=signal, confidence=confidence, raw_value=avg_pred)


def confidence_weighted(predictions: Sequence[Prediction], threshold: float) -> Prediction:
    """Weight each model's raw prediction by its own confidence score.

    Models that are more certain about their prediction contribute more.
    Falls back to simple mean when all confidences are zero.
    """
    confidences = np.array([p.confidence for p in predictions])
    raw_values = np.array([p.raw_value for p in predictions])

    total_conf = confidences.sum()
    avg_pred = float(
        np.dot(confidences / total_conf, raw_values) if total_conf > 0
        else raw_values.mean()
    )

    confidence = min(1.0, abs(avg_pred) / max(threshold * 2, 1e-9))

    if avg_pred > threshold:
        signal = "buy"
    elif avg_pred < -threshold:
        signal = "sell"
    else:
        signal = "hold"

    return Prediction(signal=signal, confidence=confidence, raw_value=avg_pred)


def unanimous(predictions: Sequence[Prediction]) -> Prediction:
    """Only trade when every model agrees on the same non-hold direction.

    Most conservative strategy — eliminates conflicting signals entirely.
    """
    non_hold = [p for p in predictions if p.signal != "hold"]
    directions = {p.signal for p in non_hold}

    all_agree = len(non_hold) == len(predictions) and len(directions) == 1
    signal = non_hold[0].signal if all_agree else "hold"

    confidence = float(np.mean([p.confidence for p in non_hold])) if all_agree else 0.0
    raw_value = float(np.mean([p.raw_value for p in predictions]))
    return Prediction(signal=signal, confidence=confidence, raw_value=raw_value)
