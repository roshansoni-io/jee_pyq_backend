from __future__ import annotations

from typing import Any

import numpy as np

_norm_epsilon = 1e-12


def _nearest_centroid(centroids, vector):
    best_label = None
    best_similarity = -1.0
    for label, centroid in centroids:
        similarity = float(np.dot(vector, centroid))
        if similarity > best_similarity:
            best_similarity = similarity
            best_label = label
    return best_label, best_similarity


def _recompute_centroid(centroids, label, matrix, member_indices):
    new_centroid = matrix[member_indices].mean(axis=0)
    new_centroid = new_centroid / max(np.linalg.norm(new_centroid), _norm_epsilon)
    return [(l, new_centroid) if l == label else (l, c) for l, c in centroids]


def cluster_members(
    questions: list[Any], vectors: list[list[float]], threshold: float
) -> dict:
    if not questions:
        return {}
    matrix = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.maximum(norms, _norm_epsilon)

    centroids: list[tuple[int, np.ndarray]] = []
    member_indices: dict[int, list[int]] = {}
    clusters: dict[int, list[Any]] = {}

    for index, (vector, question) in enumerate(zip(matrix, questions)):
        best_label, best_similarity = _nearest_centroid(centroids, vector)
        if best_label is not None and best_similarity >= threshold:
            member_indices[best_label].append(index)
            clusters[best_label].append(question)
            centroids = _recompute_centroid(
                centroids, best_label, matrix, member_indices[best_label]
            )
        else:
            label = len(centroids)
            centroids.append((label, vector))
            member_indices[label] = [index]
            clusters[label] = [question]
    return clusters
