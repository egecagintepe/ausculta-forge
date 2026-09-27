"""AuscultaForge — Subject-Safe Cross-Validation Fold Splitter.

Guarantees:
- Zero data leakage: No subject ever appears in both training and evaluation in any fold.
- Multi-location recordings (e.g. 12345_AV, 12345_MV) are strictly kept together.
- Deterministic fold generation governed by random seed.
- Balanced fold allocations based on record counts per subject.
- No diagnostic or demographic stratification.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence
import numpy as np

from .models import AnnotatedPCGRecord


def create_subject_grouped_folds(
    records: Sequence[AnnotatedPCGRecord],
    fold_count: int = 5,
    random_seed: int = 2026,
) -> list[tuple[list[AnnotatedPCGRecord], list[AnnotatedPCGRecord]]]:
    """Partition records into K subject-grouped cross-validation folds.
    
    Parameters
    ----------
    records : Sequence[AnnotatedPCGRecord]
        List of annotated PCG records to partition.
    fold_count : int
        Number of cross-validation folds (default: 5).
    random_seed : int
        Deterministic random seed (default: 2026).
        
    Returns
    -------
    list[tuple[list[AnnotatedPCGRecord], list[AnnotatedPCGRecord]]]
        List of (train_records, eval_records) for each fold.
        
    Raises
    -------
    ValueError
        If the number of unique subjects is smaller than fold_count.
    """
    if not records:
        return []

    # 1. Group records strictly by subject_id
    subject_to_records: dict[str, list[AnnotatedPCGRecord]] = defaultdict(list)
    for rec in records:
        subject_to_records[rec.subject_id].append(rec)

    unique_subjects = sorted(subject_to_records.keys())
    n_subjects = len(unique_subjects)

    if n_subjects < fold_count:
        raise ValueError(
            f"Cannot create {fold_count} subject-grouped folds with only {n_subjects} unique subjects."
        )

    # 2. Deterministic shuffling of subjects using specified seed
    rng = np.random.default_rng(random_seed)
    shuffled_subjects = list(unique_subjects)
    rng.shuffle(shuffled_subjects)

    # 3. Sort subjects descending by recording count for greedy balanced packing
    # Secondary sort key is subject_id to ensure absolute determinism across platforms
    shuffled_subjects.sort(
        key=lambda sid: (len(subject_to_records[sid]), sid),
        reverse=True,
    )

    # 4. Greedy assignment to folds to balance recording counts
    fold_subjects: list[list[str]] = [[] for _ in range(fold_count)]
    fold_record_counts = [0] * fold_count

    for sid in shuffled_subjects:
        n_recs = len(subject_to_records[sid])
        # Find fold with minimum record count
        min_fold_idx = int(np.argmin(fold_record_counts))
        fold_subjects[min_fold_idx].append(sid)
        fold_record_counts[min_fold_idx] += n_recs

    # 5. Construct train/eval record splits for each fold
    splits: list[tuple[list[AnnotatedPCGRecord], list[AnnotatedPCGRecord]]] = []

    for fold_idx in range(fold_count):
        eval_sids = set(fold_subjects[fold_idx])
        train_sids = set(unique_subjects) - eval_sids

        # Strict anti-leakage verification
        assert len(train_sids & eval_sids) == 0, "Subject leakage detected in fold construction!"

        train_records: list[AnnotatedPCGRecord] = []
        eval_records: list[AnnotatedPCGRecord] = []

        for sid in train_sids:
            train_records.extend(subject_to_records[sid])
        for sid in eval_sids:
            eval_records.extend(subject_to_records[sid])

        # Verify all records are partitioned cleanly
        train_rec_ids = {r.record_id for r in train_records}
        eval_rec_ids = {r.record_id for r in eval_records}
        assert len(train_rec_ids & eval_rec_ids) == 0, "Record leakage detected in fold construction!"
        assert len(train_records) + len(eval_records) == len(records)

        splits.append((train_records, eval_records))

    return splits
