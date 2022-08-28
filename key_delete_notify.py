# Check for keys over a certain age, deactivate and delete them, then notify the user and the IT team
import boto3
from botocore.exceptions import ClientError
import datetime
import json
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

# deactivate the IAM key
def deactivate_key(access_key, username):
    try:
        iam_client.update_access_key(UserName=username, AccessKeyId=access_key, Status="Inactive")
        print(access_key + " deactivated.")
    except ClientError as e:
        print("The access key with id %s cannot be found" % access_key)

#delete the IAM key
def delete_key(access_key, username):
    try:
        iam_client.delete_access_key(UserName=username, AccessKeyId=access_key)
        print (access_key + " deleted.")
    except ClientError as e:
        print("The access key with id %s cannot be found" % access_key)

# create a new key for user
def create_key(username):
    access_key_metadata = iam_client.create_access_key(UserName=username)
    access_key = access_key_metadata['AccessKey']['AccessKeyId']
    secret_key = access_key_metadata['AccessKey']['SecretAccessKey']

# notify target address(s) and user
def send_plain_email(username, access_key):
    ses_client = boto3.client("ses", region_name="us-east-1")
    CHARSET = "UTF-8"
    SENDER = "it@company.com"
    RECIPIENT = "it@company.com"
    SUBJECT = "AWS IAM - Credenitals Expired!"
    response = ses_client.send_email(
        Destination={
            "ToAddresses": [
                RECIPIENT,
                #username
            ],
        },
        Message={
            "Body": {
                "Text": {
                    "Charset": CHARSET,
                    "Data": username + " - " + access_key + "\n IAM key expired. \nPlease open a ticket with IT to request new credentials.",
                }
            },
            "Subject": {
                "Charset": CHARSET,
                "Data": SUBJECT,
            },
        },
        Source= SENDER,
    )

# iterate accross users that match a desired pattern and call desired functions to deactivate, delete, create, or notify
def lambda_handler(event, context):
    details = iam_client.list_users(MaxItems=300)
    users = details['Users']
    for user in users:
        user_iam_details=list_key(user=user["UserName"], age=90, status='Active') # set age to expiration date
        for _ in user_iam_details:
                username = user["UserName"]
                if '@company.com' in username:
                    deactivate_key(access_key=_['AccessKeyId'], username=_['UserName'])
                    delete_key(access_key=_['AccessKeyId'], username=_['UserName'])
                    #create_key(username=_['UserName'])
                    print(user["UserName"] + " - " + _['AccessKeyId'] + " Key Deleted")
                    send_plain_email(access_key=_['AccessKeyId'], username=_['UserName'])
