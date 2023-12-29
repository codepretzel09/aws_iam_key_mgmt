# Check for keys about to expire and notifiy users along with the IT team
import boto3
import json
from botocore.exceptions import ClientError
import datetime
iam_client = boto3.client('iam')

# list keys and iam details
def list_key(user, age, status):
    keyinfo=iam_client.list_access_keys(UserName=user)
    key_details={}
    user_iam_details=[]
    
    for keys in keyinfo['AccessKeyMetadata']:
        if (days:=diff_time(keys['CreateDate'])) >= age and keys['Status']==status:
            key_details['UserName']=keys['UserName']
            key_details['AccessKeyId']=keys['AccessKeyId']
            key_details['days']=days
            key_details['status']=keys['Status']
            user_iam_details.append(key_details)
            key_details={}
    
    return user_iam_details

# check age of key
def diff_time(keycreatedtime):
    now=datetime.datetime.now(datetime.timezone.utc)
    diff=now-keycreatedtime
    return diff.days

# notify target address(s) and user
def send_plain_email(username, access_key):
    ses_client = boto3.client("ses", region_name="us-east-1")
    CHARSET = "UTF-8"
    SENDER = "it@company.com"
    RECIPIENT = "it@company.com"
    SUBJECT = "Red Canary AWS IAM - Credenitals Notifaction"
    response = ses_client.send_email(
        Destination={
            "ToAddresses": [
                RECIPIENT,
               # username
            ],
        },
        Message={
            "Body": {
                "Text": {
                    "Charset": CHARSET,
                    "Data": username + " - " + access_key + "\nYour IAM Keys are set to expire in 10 days. \nPlease open a ticket with IT to request new credentials.",
                }
            },
            "Subject": {
                "Charset": CHARSET,
                "Data": SUBJECT,
            },
        },
        Source= SENDER,
    )

# iterate accross users that match a desired pattern and call desired functions to notify users of keys approaching expiration
def lambda_handler(event, context):
    details = iam_client.list_users(MaxItems=300)
    users = details['Users']
    for user in users:
        user_iam_details=list_key(user=user["UserName"], age=80, status='Active') # set age to desired days to warn before expiration
        for _ in user_iam_details:
                username = user["UserName"]
                if '@company.com' in username:
                    print(user["UserName"] + " - " + _['AccessKeyId'] + " Notification Sent")
                    send_plain_email(access_key=_['AccessKeyId'], username=_['UserName'])
