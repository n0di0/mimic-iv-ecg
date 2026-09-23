# mimic-iv-ecg
temp workspace for wfu buildathon! 

[9-22-26] DATA
- Attempted to download the full MIMIC-IV-ECG
- Restarted download 3x before terminating it
- Refocused on the scope in the team plan, stopped wgetting everything

[9-23-26] DATA
- Created python script to save only eligible patients (93% of records, 742,691 records) 
- Used aria2c, which allowed me to send out multiple file download requests at once
- ETA on filtered dataset, 6hrs
- **filter_eligible_patients.py**, what i used to make sure the data we used had 2x patients
- **eligible_patients.csv**, the patients that were valuable by their id + how many studies they have


