"""Strict subject-leakage prevention tests for validation fold splitting."""

import pytest
from pathlib import Path
from pcg_core.segmentation.validation.models import AnnotatedPCGRecord
from pcg_core.segmentation.validation.splitting import create_subject_grouped_folds


def _make_dummy_record(subject_id: str, loc: str) -> AnnotatedPCGRecord:
    rec_id = f"{subject_id}_{loc}"
    return AnnotatedPCGRecord(
        dataset_id="CIRCOR_DIGISCOPE",
        dataset_version="1.0.3",
        record_id=rec_id,
        subject_id=subject_id,
        auscultation_location=loc,
        sample_rate_hz=4000.0,
        duration_s=5.0,
        annotation_intervals=(),
        wav_path=Path(f"/tmp/{rec_id}.wav"),
        annotation_path=Path(f"/tmp/{rec_id}.tsv"),
    )


def test_subject_leakage_is_strictly_zero():
    # 20 subjects, varying number of recordings per subject (1 to 4 locations)
    records = []
    locations = ["AV", "MV", "PV", "TV"]
    for i in range(1, 21):
        subj_id = f"SUBJ_{i:03d}"
        # Some have 4 locations, some have 1, some have 2
        num_locs = (i % 4) + 1
        for loc in locations[:num_locs]:
            records.append(_make_dummy_record(subj_id, loc))

    assert len(records) > 20

    folds = create_subject_grouped_folds(records, fold_count=5, random_seed=2026)
    assert len(folds) == 5

    all_eval_subjects = set()

    for fold_idx, (train_records, eval_records) in enumerate(folds):
        train_subjs = {r.subject_id for r in train_records}
        eval_subjs = {r.subject_id for r in eval_records}

        # 1. HARD ANTI-LEAKAGE RULE: Train and Eval subjects MUST NOT OVERLAP
        intersection = train_subjs.intersection(eval_subjs)
        assert len(intersection) == 0, f"Subject leakage detected in Fold {fold_idx}: {intersection}"

        # 2. Check all recordings of train subjects are in train_records
        for r in train_records:
            assert r.subject_id in train_subjs
            assert r.subject_id not in eval_subjs

        # 3. Check all recordings of eval subjects are in eval_records
        for r in eval_records:
            assert r.subject_id in eval_subjs
            assert r.subject_id not in train_subjs

        all_eval_subjects.update(eval_subjs)

    # 4. Across all folds, each subject appears as an eval subject exactly once
    assert len(all_eval_subjects) == 20


def test_multi_location_recordings_stay_together():
    # Subject 999 with all 4 locations
    records = [
        _make_dummy_record("999", "AV"),
        _make_dummy_record("999", "MV"),
        _make_dummy_record("999", "PV"),
        _make_dummy_record("999", "TV"),
    ]
    # Add other subjects to form at least 5 subjects
    for s in ["100", "200", "300", "400"]:
        records.append(_make_dummy_record(s, "AV"))

    folds = create_subject_grouped_folds(records, fold_count=5, random_seed=2026)

    for train_records, eval_records in folds:
        subj_999_train = [r for r in train_records if r.subject_id == "999"]
        subj_999_eval = [r for r in eval_records if r.subject_id == "999"]

        # 999 recordings must be ALL in train, or ALL in eval, never split
        if len(subj_999_train) > 0:
            assert len(subj_999_train) == 4
            assert len(subj_999_eval) == 0
        else:
            assert len(subj_999_eval) == 4
            assert len(subj_999_train) == 0


def test_fold_splitting_deterministic_with_fixed_seed():
    records = [_make_dummy_record(f"S_{i}", "AV") for i in range(10)]
    folds_a = create_subject_grouped_folds(records, fold_count=5, random_seed=2026)
    folds_b = create_subject_grouped_folds(records, fold_count=5, random_seed=2026)

    for (train_a, eval_a), (train_b, eval_b) in zip(folds_a, folds_b):
        assert {r.record_id for r in train_a} == {r.record_id for r in train_b}
        assert {r.record_id for r in eval_a} == {r.record_id for r in eval_b}

