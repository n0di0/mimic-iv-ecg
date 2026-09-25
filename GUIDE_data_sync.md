# Dataset Syncing Guide

Here is a quick guide in using the scripts to make sure we're all going off of the same dataset. 
If we are all testing and looking at the same dataset, then we can all make educated guesses on our data and make proper next steps, instead of different people having different values. These tools will help us work with one single source of truth.

Although thank you guys for keeping it going even when I am behind on my deliverables, lol.

***
### Files:
eligible_records_downloaded.csv
- lives on my computer originally, greater than 2 studies, and all confirmed on disk
- will soon be uploaded to drive
- will be compared with what data you have

split_manifest.json
- the frozen train/val/test patient assignment
- the seed is 42 (claude picked that number lol)
- i made sure there were verification checks throughout, you will see it in the console
- lives in the github repo

### Current Numbers:
- eligible patients (Nelig): 32,457
- eligible records on disk: 232,756
- split: train=22,719 / val=4,868 / test=4,870

These are the numbers of the dataset that we can all use, a strong baseline

### How to use

*1A Check what you're missing from the eligible_records_downloaded (linux)*

  >``# Generate a list of what you've actually got on disk
find .
  > -name "*.dat" -exec basename {} .dat \; > my_downloaded_study_ids.txt``

*1B Compare against the canonical set (linux)*
  >``python3 check_my_downloads.py \
    --canonical eligible_records_downloaded.csv \
    --my-downloaded my_downloaded_study_ids.txt \
    --out missing_paths.txt``

It'll say you have everything, or you have some but not all of the files.
If you have everything, you're good to go! If you don't, keep going down the steps

*2 Download what's missing*

It will also output missing_paths.txt if you don't have what the basic dataset has. 

You can feed it into the download method here;

aria2c, linux specific i believe:

  >```aria2c -c -j 4 -i missing_paths.txt --dir=./mimic_full```

aws s3 (recommended, any terminal but you need access):
  >``aws s3 cp s3://physionet-mimic-iv-ecg/ ./mimic_full --recursive \
    --exclude "*" --include-from missing_paths.txt``

Make sure to adjust the flags to your own naming conventions.
Also, follow the other guide if needed to set up AWS for the credentials and access.

*3 Double check*

If you had missing files, double check and run it until you have everything. 

A double pass is best to make sure we are all working from the same thing.

It is actually better if you have more, but this is a sample training size that isnt overwhelming on our machines that everyone has access to.



