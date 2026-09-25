"""
What it does:
- Tells you what MIMIC files you're missing to match the eligible-patient set
- No need to re-run filter_eligible_patients.py for training purposes because of this
- Just need to point this at your downloaded_study_ids.txt, and this will tell you what data to grab

Syntax:
    python3 check_my_downloads.py \
        --canonical eligible_records_downloaded.csv \
        --my-downloaded downloaded_study_ids.txt \
        --out missing_paths.txt
        
Input:
- the eligible_records_downloaded.csv that will be uploaded to the drive, the records for training
- your own downloaded_study_ids.txt from your own install

Output:
    missing_paths.txt -- .hea and .dat paths you still need to download,
    in the same files/pNNNN/pXXXXXXXX/sZZZZZZZZ/ZZZZZZZZ format used by
    download_paths.txt, so it can be fed straight into aria2c or aws s3.
"""

import argparse
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", required=True,
                     help="The team's eligible_records_downloaded.csv (shared, do not regenerate)")
    ap.add_argument("--my-downloaded", required=True,
                     help="Your own downloaded_study_ids.txt, from `find . -name '*.dat' -exec basename {} .dat \\;`")
    ap.add_argument("--out", default="missing_paths.txt")
    args = ap.parse_args()

    canonical = pd.read_csv(args.canonical, dtype=str)
    canonical["study_id"] = canonical["study_id"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

    with open(args.my_downloaded) as f:
        mine = set(line.strip() for line in f if line.strip())

    canonical_ids = set(canonical["study_id"])
    missing_ids = canonical_ids - mine
    already_have = canonical_ids & mine

    print(f"Canonical eligible study_ids (team's frozen set): {len(canonical_ids)}")
    print(f"You already have: {len(already_have)}")
    print(f"You are MISSING: {len(missing_ids)}")

    if not missing_ids:
        print("\nYou already have everything in the canonical set. Nothing to download.")
        return

    missing_rows = canonical[canonical["study_id"].isin(missing_ids)]

    with open(args.out, "w") as f:
        for _, row in missing_rows.iterrows():
            subject_id = row["subject_id"]
            study_id = row["study_id"]
            shard = f"p{subject_id[:4]}"
            f.write(f"files/{shard}/p{subject_id}/s{study_id}/{study_id}.hea\n")
            f.write(f"files/{shard}/p{subject_id}/s{study_id}/{study_id}.dat\n")

    print(f"\nWrote {len(missing_rows)} missing records "
          f"({len(missing_rows)*2} files) to {args.out}")
    print("Feed this into your download tool of choice (aria2c -i, or aws s3 cp --recursive with this list).")

    # Also flag: how many missing records belong to patients you have SOME
    # but not all recordings for -- these are silent leakage risks if you
    # try to use partial data before finishing the download
    my_patients_all = canonical[canonical["subject_id"].isin(
        canonical[canonical["study_id"].isin(mine)]["subject_id"]
    )]
    partial_patients = my_patients_all[
        my_patients_all["subject_id"].isin(missing_rows["subject_id"])
    ]["subject_id"].nunique()
    if partial_patients:
        print(f"\nWARNING: {partial_patients} patient(s) have SOME but not ALL "
              f"recordings downloaded. Do not use these patients for pairing "
              f"until the download finishes -- a partial patient can silently "
              f"produce fewer or wrong pairs.")


if __name__ == "__main__":
    main()
