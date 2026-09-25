# Downloading MIMIC IV ECG via AWS S3
A great alternative to wget and trying to install it from the website. Instead of a 3-4 day download. This guide is Linux / Powershell!

***

## LINUX
### 1 - Create an account on PhysioNet
Once you've created an account, you will see that you can use the AWS command line to download the data under the "Access the files" section.

### 2 - Log into your AWS (or create an account)
The free tier works, create an account using the regular channels. No need to set up 2FA yet.

### 3 - Get AWS access keys
In the AWS website at this link (https://us-east-1.console.aws.amazon.com/console/home?region=us-east-1), follow this path.
- Search IAM in the search bar and select it
- Go to the left menu, then select IAM Users 
- Create a new user (any name is fine, no need for the management console)
- In permissions options, select "Add user to group"
- At the bottom under "User groups", create a group
- Enter a group name (any name is fine), search for the policy "AmazonS3FullAccess," then create the group 
- Exit out, head back to IAM Users and click "Create Access Key"
- For the use case, select Command Line Interface and proceed through (description tag isn't necessary)
- Save your Access key and your Secret access key on your local machine, they will be your credentials to log in later

### 4 - Link your AWS Account to PhysioNet
Finish verification, and get access to the real bucket
- Head to settings, then look for cloud settings, and enter your AWS account ID. It will verify quickly.
- Once you're done in settings, head back to the MIMIC IV ECG dataset, and head back to "Access the files"
- Follow the verification steps with your Access key and Secret access key
- Mine looked like the following: aws s3 sync s3://arn:aws:s3:us-east-1:724665945834:accesspoint/mimic-iv-ecg-v1-0-01/mimic-iv-ecg/1.0/ DESTINATION
- Replace DESTINATION with a better folder name (I used MimicDataAWS). 

### 5 - Run the AWS download in tmux
It will run for hours, so protect it in case you lose connection or close the terminal.
- Open up linux
- Use the command: tmux new -s mimic_download aws s3 sync s3://**<your-confirmed-path>**/ MimicDataAWS
- You can detach with Ctrl+b, then press d. You can reattach using tmux attach -t mimic_download.
- Attaching and reattaching just means the session can continue in the background 
- To stop the download, hit Ctrl+C, the aws s3 sync process will stop cleanly
- To resume the download in tmux, run these commands:
- Visually and easily examine the file using your file explorer GUI with the command: explorer.exe .
- Afterwards, run: tmux attach -t mimic_download | aws s3 sync s3://**<your-confirmed-path>**/ MimicDataAWS

***

## PowerShell
- Run powershell in admin mode
  - Have to escalate, will throw an error if you do not

- Install the AWS Powershell Command Line module:
  - winget install Amazon.AWSCLI
  - You will see Windows installer pop up, which is fine, let that install too

- Once it's successfully installed, close out of all Powershell windows

- Grab your AWS credentials
  - (Skip back to the section where you create an account and make a user and a group, then save those access and secret keys for here)

- After a second, open another admin mode powershell, then run
  - aws --version

- You should get

  - aws-cli/2.37.2 Python/3.14.6 Windows/... or something similar

  - If you do not, troubleshoot with your AI, but you most likely will

- Type in
  - aws configure

- Then you'll get a few questions that pop up:
  - Access Key ID: Access key  
  - Secret Access Key: Secret access key
  - Default region name: us-east-1
  - Default output format: json

- Then, head to where the dataset is in PhysioNet
  - https://physionet.org/content/mimic-iv-ecg/1.0/

- Link your PhysioNet account to your AWS creds
  - Create a PhysioNet account, head to settings, look for cloud, and follow the above instructions to verify your account

- It will ask you to paste some things into your terminal, ask your AI how to format them for powershell but I think they are roughly the same because it is aws terminal

- Once that is all set up, head back to the dataset Mimic IV ECG

- By Access Files, you'll now see a new thing that allows you to access files with AWS command line tools (not linux specific), something like this:
  - aws s3 sync s3://arn:aws:s3:us-east-1:724665945834:accesspoint/mimic-iv-ecg-v1-0-01/mimic-iv-ecg/1.0/ DESTINATION (that is what mine looked like)
  - Change "DESTINATION" to a regular folder name like Mimic_IV_ECG before you hit enter, and it will start downloading onto your machine!
 
***

I have a copy of the sample on my machine, but I feel like acquiring it from AWS would be quicker and safer.
Let me know if you have any questions, pop this into your AI of choice to walk through as well.
Once everyone has the same basic files downloaded, we can then filter through the patient_ids using my script in GitHub.
After this, we all should be working with same data and have a single source of truth. 
