import sys

import pyotp
from new_random_str import so_random
from hash import hash
import dotenv
import json
import boto3
import os
dotenv.load_dotenv()

def roll_creds(secret_it=None, update=False):
    secrets = dict()
    secrets["OTS_SECRET"] = pyotp.random_base32()
    secrets["VACUUMSALT"] = so_random()
    secrets["VACUUMROOTUSER"] = so_random()
    secrets["VACUUMAPIKEYSALT"]=so_random()
    secrets["VACUUMSESSIONKEY"]=so_random()
    new_pwd=so_random()
    secrets["VACUUMROOTHASH"]= hash(new_pwd, secrets["VACUUMSALT"])
    if not secret_it:
        secret_id = os.environ.get("AWS_SECRET_ID")
    if not update:
        print(f"new password is: {new_pwd}")
        print(secrets)
    else:
        print(f"new password is: {new_pwd}")
        print(f"your new OTS is {secrets['OTS_SECRET']}")
        secmgrclient = boto3.client('secretsmanager', region_name=os.environ.get("AWS_REGION"))
        response = secmgrclient.update_secret(SecretId=secret_it, SecretString=json.dumps(secrets))
        print(response)
if __name__ == "__main__":
    if len(sys.argv)==2:
        roll_creds(sys.argv[1], update=True)
    else:
        print("Creds not updated in amazon, to update specify secret id")
        roll_creds(update=False)