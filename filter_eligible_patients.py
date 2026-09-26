"""
What it does:
- Filters the record_list.csv down to patients with more than one study to make sure we work with good samples
- Collects subject and study id, and generates the exact file paths to download
- Cross references theoretically eligible records against the record_list.csv to see what patients on disk have >=2 studies.

Input:
- record_list.csv, the MIMIC-IV-ECG patient/study index
- downloaded_study_ids.txt, one study_id per line, from 'find . -name "*dat"' command

Output:
- eligible_patients.csv, with each relevant subject_id and how many studies they have
- eligible_records.csv, filtered record_list
- download_paths.txt, for .hea and .dat
- eligible_records_downloaded.csv, from the --check-downloaded step
- prints the real "N-elig", how many eligible patients are confirmed on disk

Usage:
    # Step 1 (run once, whenever record_list.csv changes -- it hasn't since 9/23):
    python3 filter_eligible_patients.py --build --record-list record_list.csv

    # Step 2 (run anytime you want a fresh on-disk eligibility count):
    python3 filter_eligible_patients.py --check-downloaded \
        --eligible eligible_records.csv --downloaded downloaded_study_ids.txt
"""

import argparse
import pandas as pd


def main(record_list_path: str):
    df = pd.read_csv(record_list_path, dtype=str)

    print(f"Total records: {len(df)}")
    print(f"Total unique subject_id: {df['subject_id'].nunique()}")

    # Count studies per patient
    counts = df.groupby("subject_id")["study_id"].nunique().reset_index()
    counts.columns = ["subject_id", "study_count"]

    eligible = counts[counts["study_count"] >= 2]
    print(f"Eligible patients (>=2 studies): {len(eligible)}")

    eligible_ids = set(eligible["subject_id"])
    eligible_records = df[df["subject_id"].isin(eligible_ids)].copy()
    print(f"Eligible records (recordings to download): {len(eligible_records)}")

    # Save outputs
    eligible.to_csv("eligible_patients.csv", index=False)
    eligible_records.to_csv("eligible_records.csv", index=False)

    # Build the exact MIMIC file paths per the documented structure:
    # files/pNNNN/pXXXXXXXX/sZZZZZZZZ/ZZZZZZZZ
    with open("download_paths.txt", "w") as f:
        for _, row in eligible_records.iterrows():
            subject_id = row["subject_id"]
            study_id = row["study_id"]
            shard = f"p{subject_id[:4]}"
            f.write(f"files/{shard}/p{subject_id}/s{study_id}/{study_id}.hea\n")
            f.write(f"files/{shard}/p{subject_id}/s{study_id}/{study_id}.dat\n")

    print("\nWrote: eligible_patients.csv, eligible_records.csv, download_paths.txt")


def check_downloaded_eligibility(eligible_records_path: str, downloaded_ids_path: str):
    """
    Cross-references the theoretical eligible_records.csv (computed against
    the full record_list.csv) with what's actually been downloaded, to find
    out how many patients have >=2 studies ACTUALLY ON DISK.

    Input:
    - eligible_records.csv, from main() above
    - downloaded_study_ids.txt, one study_id per line, from `find . -name "*.dat"`

    Output:
    - eligible_records_downloaded.csv, eligible records that are actually downloaded
    - prints the real Nelig (eligible patient count) for the data you actually have
    """
    eligible = pd.read_csv(eligible_records_path, dtype=str)

    with open(downloaded_ids_path) as f:
        downloaded = set(line.strip() for line in f if line.strip())

    print(f"Theoretically eligible records (full dataset): {len(eligible)}")
    print(f"Study_ids actually downloaded: {len(downloaded)}")

    eligible["downloaded"] = eligible["study_id"].isin(downloaded)
    on_disk = eligible[eligible["downloaded"]].copy()

    print(f"Eligible records actually on disk: {len(on_disk)}")

    # Recount studies per patient, but only counting studies actually downloaded
    counts_on_disk = on_disk.groupby("subject_id")["study_id"].nunique().reset_index()
    counts_on_disk.columns = ["subject_id", "study_count_on_disk"]

    truly_eligible = counts_on_disk[counts_on_disk["study_count_on_disk"] >= 2]
    print(f"Patients with >=2 studies ACTUALLY DOWNLOADED: {len(truly_eligible)}")

    truly_eligible_ids = set(truly_eligible["subject_id"])
    final = on_disk[on_disk["subject_id"].isin(truly_eligible_ids)]
    final.to_csv("eligible_records_downloaded.csv", index=False)
    print(f"\nWrote eligible_records_downloaded.csv with {len(final)} rows, "
          f"{final['subject_id'].nunique()} patients")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true",
                         help="Run the one-time build step against the full record_list.csv")
    parser.add_argument("--check-downloaded", action="store_true",
                         help="Cross-check eligible_records.csv against downloaded_study_ids.txt")
    parser.add_argument("--record-list", default="record_list.csv")
    parser.add_argument("--eligible", default="eligible_records.csv")
    parser.add_argument("--downloaded", default="downloaded_study_ids.txt")
    args = parser.parse_args()

    if not args.build and not args.check_downloaded:
        parser.error("Pass --build and/or --check-downloaded. See the module docstring for usage.")

    if args.build:
        main(args.record_list)

    if args.check_downloaded:
        check_downloaded_eligibility(args.eligible, args.downloaded)
