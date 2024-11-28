import boto3
import os
import logging
from werkzeug.utils import secure_filename
from Crypto.SelfTest.Cipher.test_OFB import file_name
logger = logging.getLogger(__name__)

bucket_name = os.environ.get("CDN_BUCKET_NAME")
if os.environ.get("AWS_PROFILE_NAME"):
    session = boto3.Session(profile_name=os.environ.get("AWS_PROFILE_NAME"))#profile_name='vacuum'
else:
    session = boto3.Session()
s3 = session.client('s3')

def list_files(_bucket_name=bucket_name):
    """
    Function to list files in a given S3 bucket
    """
    contents = dict()
    count = 0
    for item in s3.list_objects(Bucket=_bucket_name)['Contents']:
        filesplit = item["Key"].split(".")
        fileext = filesplit[-1]
        item["fileext"] = fileext
        contents[item['Key']] = item
        count+=1
    return contents

def download_file(file_name, _bucket_name=bucket_name):
    """
    Function to download a given file from an S3 bucket
    """
    just_file_name =os.path.basename(file_name)
    output = f"downloads/{just_file_name}"
    dls3 = session.resource('s3')
    logger.info(f"trying to download s3 file {just_file_name} from bucket {_bucket_name}")
    dls3.Bucket(_bucket_name).download_file(file_name, output)

    return output

def mv_file(file_name, new_name):
        # Copy the old file to the new file location
    s3.copy_object(Bucket=bucket_name, CopySource={'Bucket': bucket_name, 'Key': file_name}, Key=new_name)
    files = list_files()#sloppy but will work
    if new_name in files:
        # Delete the old file
        s3.delete_object(Bucket=bucket_name, Key=file_name)

def create_folder(folder_name):
    # Ensure the folder name ends with a slash
    if not folder_name.endswith('/'):
        folder_name += '/'
    s3.put_object(Bucket=bucket_name, Key=folder_name)
def s3_upload_file(tempfile,filename,_bucket_name=bucket_name):
    s3.upload_fileobj(Fileobj=tempfile
                      ,Bucket=_bucket_name
                      ,Key=secure_filename(filename))

def s3_remove_file(filename, _bucket_name=bucket_name):
     s3.delete_object(Bucket=_bucket_name, Key=filename)
