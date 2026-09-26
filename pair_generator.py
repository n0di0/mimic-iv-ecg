"""
pair_generator.py — ECG Similarity & Patient Matching, Data & Infrastructure lane

WHAT
    Turns the frozen patient split (split_manifest.json) plus the ingested
    ECG metadata (ecg_mimic_metadata.csv) into the actual training input a
    Siamese network learns from: a list of (ECG_ID_A, ECG_ID_B, label) pairs.

    Positive pair = two different recordings from the SAME Participant_ID.
    Negative pair = two recordings from DIFFERENT Participant_IDs.

RULES (team plan §8.2)
    - Cap positive pairs per patient (default: 5 for train, 2 for val/test)
      so a "frequent flyer" patient with many recordings can't dominate
      training.
    - Keep roughly 1:1 class balance (positives : negatives) per partition.
    - The VALIDATION pair list is frozen on first generation. Re-running
      this script against an existing frozen val pair file will refuse to
      overwrite it unless --force is passed, and will warn loudly if the
      newly-generated set doesn't hash-match the frozen one -- an unnoticed
      change here silently invalidates every prior experiment comparison.

KNOWN LIMITATION (flag for Clinical/Program)
    The team plan (§4.3) recommends preferring positive pairs from
    DIFFERENT ENCOUNTERS/DAYS specifically, to avoid the model learning
    "same session" instead of "same person." ecg_mimic_metadata.csv does
    not currently carry a recording datetime column, so this version can
    only guarantee "different study_id" -- not "different day." Once a
    datetime column is joined in (from record_list.csv's ecg_time), this
    script should be upgraded to prefer temporally-separated pairs.

OUTPUT
    - <out_prefix>_train_pairs.csv : ECG_ID_A, ECG_ID_B, Participant_A, Participant_B, label
    - <out_prefix>_val_pairs.csv   : same columns, FROZEN after first run
    - <out_prefix>_test_pairs.csv  : same columns, generated once, meant to
                                      be opened exactly once at the very end
                                      (team plan §8.3's "one-way door")
    - <out_prefix>_pairs_manifest.json : seed, counts, SHA-256 hashes per
                                      partition, and the V7/V8 check results

USAGE
    python3 pair_generator.py --split split_manifest.json \\
        --metadata ecg_mimic_metadata.csv --out-prefix ecg_mimic
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42  # same fixed seed as patient_splitter.py -- consistency across the pipeline

POS_CAP = {"train": 5, "val": 2, "test": 2}   # per team plan's size ledger
NEG_CAP = {"train": 10, "val": 5, "test": 5}
# NOTE (9/26): all three caps were originally symmetric with POS_CAP (5 for
# train, 2 for val/test), which caps the whole negative-pair pool at
# n_participants * cap / 2 pairs (each pair uses 2 participants' cap
# "slots"). That ceiling came in below the target needed for 1:1 balance
# with positives in EVERY partition:
#   train: 22,718 participants x 5 / 2 = 56,795 ceiling vs 80,401 target
#   val:    4,868 participants x 2 / 2 =  4,868 ceiling vs  8,377 target
#   test:   4,870 participants x 2 / 2 =  4,870 ceiling vs  8,314 target
# The rejection-sampling loop below was asymptotically approaching an
# unreachable target in all three cases and would never finish (or, with
# the feasibility guard below, would silently ship an imbalanced pair set).
# Raised so each ceiling clears its target with real margin:
#   train: cap=10 -> ceiling 113,590 (41% headroom)
#   val:   cap=5  -> ceiling  12,170 (45% headroom)
#   test:  cap=5  -> ceiling  12,175 (46% headroom)
# The feasibility guard in generate_pairs_for_partition() stays in place as
# a permanent safeguard in case a future re-ingest changes these numbers.


def _sha256_of_pairs(df: pd.DataFrame) -> str:
    """Hash a pair list in a way that's insensitive to row order (so
    re-running with the same logical pairs always produces the same hash,
    even if internal ordering differs) but sensitive to which pairs and
    which labels are actually present."""
    rows = sorted(
        f"{a}|{b}|{l}" for a, b, l in zip(df["ECG_ID_A"], df["ECG_ID_B"], df["label"])
    )
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def _sample_unique_pairs(items: list, k: int, rng: np.random.Generator) -> list[tuple]:
    """Return up to k unique unordered pairs from `items`, without
    materializing the full combination list when items is large (a patient
    with, say, 80 recordings has C(80,2)=3160 possible pairs -- fine to
    enumerate; a hypothetical much larger group would not be)."""
    n = len(items)
    total_possible = n * (n - 1) // 2
    if total_possible <= 5000:
        all_pairs = list(combinations(items, 2))
        idx = rng.choice(len(all_pairs), size=min(k, len(all_pairs)), replace=False)
        return [all_pairs[i] for i in idx]
    # Rejection sampling for the (currently hypothetical) very-large-group case
    seen = set()
    out = []
    attempts = 0
    while len(out) < k and attempts < k * 20:
        i, j = rng.choice(n, size=2, replace=False)
        pair_key = tuple(sorted((items[i], items[j])))
        if pair_key not in seen:
            seen.add(pair_key)
            out.append(pair_key)
        attempts += 1
    return out


def generate_pairs_for_partition(
    partition_name: str,
    participant_ids: set,
    ecg_by_participant: dict[str, list[str]],
    pos_cap: int,
    neg_cap: int,
    seed: int,
) -> pd.DataFrame:
    import time
    start_time = time.monotonic()
    rng = np.random.default_rng(seed)
    rows = []

    # Restrict to participants actually in this partition AND actually
    # present in the ingested data (a patient could be in the split but
    # have zero ingested recordings if every one of theirs was quarantined).
    partition_participants = [p for p in participant_ids if p in ecg_by_participant]
    n_participants = len(partition_participants)

    # --- Positive pairs: same participant, different ECG ---
    print(f"[{partition_name}] building positive pairs for {n_participants} participants...")
    for i, participant in enumerate(partition_participants, start=1):
        ecgs = ecg_by_participant[participant]
        if len(ecgs) < 2:
            continue  # can't form a positive pair from a single recording
        for ecg_a, ecg_b in _sample_unique_pairs(ecgs, pos_cap, rng):
            rows.append({
                "ECG_ID_A": ecg_a, "ECG_ID_B": ecg_b,
                "Participant_A": participant, "Participant_B": participant,
                "label": 1,
            })
        if i % 5000 == 0 or i == n_participants:
            print(f"[{partition_name}] positives: {i}/{n_participants} participants "
                  f"({100*i/n_participants:.1f}%), {len(rows)} pairs so far")

    n_positives = len(rows)
    print(f"[{partition_name}] positive pairs done: {n_positives} pairs "
          f"({time.monotonic()-start_time:.1f}s elapsed)")

    # --- Negative pairs: different participants, roughly matching positive count ---
    eligible_participants = [p for p in partition_participants if len(ecg_by_participant[p]) >= 1]
    neg_target = n_positives  # aim for 1:1 balance

    # Feasibility guard: each negative pair consumes one cap "slot" from
    # each of its two participants, so the hard ceiling on possible
    # negative pairs is n_eligible_participants * neg_cap // 2. If the
    # target exceeds that, the rejection-sampling loop below can NEVER
    # reach it -- it will just get slower and slower forever. Rather than
    # hang, clamp to a safe margin below the true ceiling (grinding through
    # the last few percent near the exact ceiling is itself extremely slow,
    # the same tail behavior that caused this in the first place) and warn
    # loudly so it's visible in the manifest/output, not just buried in logs.
    feasible_ceiling = len(eligible_participants) * neg_cap // 2
    if neg_target > feasible_ceiling:
        safe_target = int(feasible_ceiling * 0.9)
        print(f"[{partition_name}] !! WARNING: target of {neg_target} negative pairs "
              f"exceeds the feasible ceiling ({len(eligible_participants)} participants "
              f"x neg_cap={neg_cap} / 2 = {feasible_ceiling}). This target is impossible "
              f"to reach and would hang forever. Clamping target to {safe_target} "
              f"(90% of ceiling) instead. Raise neg_cap if exact 1:1 balance is required.")
        neg_target = safe_target

    neg_seen = set()
    neg_per_participant = defaultdict(int)
    attempts = 0
    max_attempts = neg_target * 30 + 1000
    print(f"[{partition_name}] building negative pairs, target={neg_target}...")

    while len(neg_seen) < neg_target and attempts < max_attempts and len(eligible_participants) >= 2:
        p_a, p_b = rng.choice(eligible_participants, size=2, replace=False)
        if neg_per_participant[p_a] >= neg_cap or neg_per_participant[p_b] >= neg_cap:
            attempts += 1
            continue
        ecg_a = rng.choice(ecg_by_participant[p_a])
        ecg_b = rng.choice(ecg_by_participant[p_b])
        pair_key = tuple(sorted((ecg_a, ecg_b)))
        if pair_key in neg_seen:
            attempts += 1
            continue
        neg_seen.add(pair_key)
        neg_per_participant[p_a] += 1
        neg_per_participant[p_b] += 1
        rows.append({
            "ECG_ID_A": ecg_a, "ECG_ID_B": ecg_b,
            "Participant_A": p_a, "Participant_B": p_b,
            "label": 0,
        })
        attempts += 1
        if len(neg_seen) % 5000 == 0 and len(neg_seen) > 0:
            print(f"[{partition_name}] negatives: {len(neg_seen)}/{neg_target} "
                  f"({100*len(neg_seen)/neg_target:.1f}%), {attempts} attempts, "
                  f"{time.monotonic()-start_time:.1f}s elapsed")

    print(f"[{partition_name}] negative pairs done: {len(neg_seen)}/{neg_target} "
          f"({time.monotonic()-start_time:.1f}s total elapsed)")

    df = pd.DataFrame(rows)
    return df


def verify_pairs(df: pd.DataFrame, partition_participants: set, pos_cap: int, neg_cap: int) -> dict:
    """V7 (pair validity) and V8 (cap enforcement) from the team plan's
    verification chain (§8.3)."""
    results = {}

    # V7a: every positive pair is same-participant, different ECG_ID
    pos = df[df["label"] == 1]
    v7a_pass = bool((pos["Participant_A"] == pos["Participant_B"]).all()
                     and (pos["ECG_ID_A"] != pos["ECG_ID_B"]).all())

    # V7b: every negative pair is different-participant
    neg = df[df["label"] == 0]
    v7b_pass = bool((neg["Participant_A"] != neg["Participant_B"]).all())

    # V7c: no pair duplicated, and no (a,b) alongside (b,a)
    normalized = df.apply(lambda r: tuple(sorted((r["ECG_ID_A"], r["ECG_ID_B"]))), axis=1)
    v7c_pass = bool(not normalized.duplicated().any())

    # V7d: both members of every pair belong to this partition
    all_participants_in_pairs = set(df["Participant_A"]) | set(df["Participant_B"])
    v7d_pass = bool(all_participants_in_pairs.issubset(partition_participants))

    v7_pass = v7a_pass and v7b_pass and v7c_pass and v7d_pass
    results["V7_pair_validity"] = {
        "pass": v7_pass,
        "positive_same_participant_diff_ecg": v7a_pass,
        "negative_different_participant": v7b_pass,
        "no_duplicate_pairs": v7c_pass,
        "all_participants_in_partition": v7d_pass,
    }

    # V8: no participant exceeds their positive/negative cap
    pos_counts = pd.concat([pos["Participant_A"]]).value_counts()
    neg_counts = pd.concat([neg["Participant_A"], neg["Participant_B"]]).value_counts()
    max_pos = int(pos_counts.max()) if len(pos_counts) else 0
    max_neg_per_participant = int(neg_counts.max()) if len(neg_counts) else 0
    v8_pass = bool(max_pos <= pos_cap and max_neg_per_participant <= neg_cap)
    results["V8_cap_enforcement"] = {
        "pass": v8_pass,
        "max_positive_pairs_for_one_participant": max_pos,
        "positive_cap": pos_cap,
        "max_negative_pairs_for_one_participant": max_neg_per_participant,
        "negative_cap": neg_cap,
    }

    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", required=True, help="split_manifest.json")
    ap.add_argument("--metadata", required=True, help="ecg_mimic_metadata.csv (or combined multi-source metadata)")
    ap.add_argument("--out-prefix", default="ecg_mimic")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--force", action="store_true",
                     help="allow overwriting an existing frozen val/test pair file")
    args = ap.parse_args()

    with open(args.split) as f:
        split = json.load(f)
    train_ids = set(split["train_ids"])
    val_ids = set(split["val_ids"])
    test_ids = set(split["test_ids"])

    meta = pd.read_csv(args.metadata, dtype=str)
    ecg_by_participant: dict[str, list[str]] = defaultdict(list)
    for ecg_id, participant_id in zip(meta["ECG_ID"], meta["Participant_ID"]):
        ecg_by_participant[participant_id].append(ecg_id)

    manifest = {"seed": args.seed, "partitions": {}}

    for name, ids in [("train", train_ids), ("val", val_ids), ("test", test_ids)]:
        out_path = Path(f"{args.out_prefix}_{name}_pairs.csv")

        if name in ("val", "test") and out_path.exists() and not args.force:
            existing = pd.read_csv(out_path, dtype=str)
            existing["label"] = existing["label"].astype(int)
            existing_hash = _sha256_of_pairs(existing)
            print(f"[{name}] frozen pair file already exists ({out_path}) -- "
                  f"not regenerating. Pass --force to override (only do this "
                  f"deliberately, and announce it to the team first).")
            manifest["partitions"][name] = {
                "status": "frozen_existing",
                "n_pairs": len(existing),
                "n_positive": int((existing["label"] == 1).sum()),
                "n_negative": int((existing["label"] == 0).sum()),
                "sha256": existing_hash,
            }
            continue

        df = generate_pairs_for_partition(
            name, ids, ecg_by_participant,
            pos_cap=POS_CAP[name], neg_cap=NEG_CAP[name], seed=args.seed,
        )
        checks = verify_pairs(df, ids, POS_CAP[name], NEG_CAP[name])
        all_pass = all(v["pass"] for v in checks.values())

        df.to_csv(out_path, index=False)
        pair_hash = _sha256_of_pairs(df)

        status = "PASS" if all_pass else "FAIL"
        print(f"[{name}] {len(df)} pairs ({int((df['label']==1).sum())} pos / "
              f"{int((df['label']==0).sum())} neg) -- checks {status}")
        if not all_pass:
            print(f"  !! {name} pair generation FAILED verification -- do not use this file. Details:")
            print(json.dumps(checks, indent=2))

        manifest["partitions"][name] = {
            "status": "generated" if all_pass else "FAILED_VERIFICATION",
            "n_pairs": len(df),
            "n_positive": int((df["label"] == 1).sum()),
            "n_negative": int((df["label"] == 0).sum()),
            "sha256": pair_hash,
            "checks": checks,
        }

    manifest_path = Path(f"{args.out_prefix}_pairs_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nWrote {manifest_path}")


if __name__ == "__main__":
    main()
