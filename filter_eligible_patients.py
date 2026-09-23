"""
What it does: 
- Filters the record_list.csv down to patients with more than one study to make sure we work with good samples
- Collects subject and study id, and generates the exact file paths to download

Input:
- record_list.csv, the MIMIC-IV-ECG patient/study index

Output:
- eligible_patients.csv, with each relevant subject_id and how many studies they have
- eligible_records.csv, filtered record_list
- download_paths.txt, for .hea and .dat
"""

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

main("record_list.csv")
