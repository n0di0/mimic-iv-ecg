# mimic-iv-ecg
temp workspace for wfu buildathon! 

### files in this repo
- guide to download MIMIC IV ECG data via AWS S3
- script to filter all eligible patients from dataset
- list of all eligible patients with 2+ studies
- daily log for data role

### daily log
[9-22-26] DATA
- Attempted to download the full MIMIC-IV-ECG
- Restarted download 3x before terminating it
- Refocused on the scope in the team plan, stopped wgetting everything

[9-23-26] DATA
- Created python script to save only eligible patients (93% of records, 742,691 records) 
- Used aria2c, which allowed me to send out multiple file download requests at once
- After 6 hours, recieved enough data to begin making essential files
- **filter_eligible_patients.py**, what I used to make sure the data we used had 2x patients
- **eligible_patients.csv**, the patients that were valubale by their id + how many studies they have
- Partial download on the MIMIC files, decided to pivot to Apple Watch files
- Downloaded Akbilgic repo
- Created a .dat to hex converter, but pivoted (too much potential for loss of data)
- Looked into a .dat to hex converter, found that WFDB .dat and .hea files can be read by wfdb-python
- **wfdb-python**, a python library that reads the files into numeric arrays, info on it in Team Manifest
- Studied how to create ingestion pipeline script in py to take raw file and output clean array
- In between utilizing **wfdb-python** or **scipy-python** (priority in keeping data as lossless as possible) 

[9-24-26] DATA
- Calculated target sample size based on Team Manifest (over 10k+ and 10k- validation pairs, cap of 2/patient)
- Target sample size, 30k eligible patients, ~18GB (19GB to be safe)
- Downloaded well over sample size, ~28GB/~90GB, which will be great to work with for now
- Investigated AWS S3 as an alternative to download instead of throttled PhysioNet HTTPS
- Set up AWS, no longer super throttled, downloaded sample size in 1.5 hours.
- Plan to look into whether or not the data skews, s3 sync is pulling folders in alphabetical subject_id
- **GUIDE_download_mimiciv_awss3**, created writeup to ensure everyone can download files quickly
- Would like to consult with Program Lead on pipeline, but for now, will stick to team plan
- Ideal pipeline: WFDB/NumPy > Float64 > Lead I > SciPy (resample_poly) > 250Hz sampling rate > 10s length > NumPy matrix > Model Training
