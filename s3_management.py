import boto3
import os
bucket_name = os.environ.get("CDN_BUCKET_NAME")
session = boto3.Session(profile_name='vacuum')
s3 = session.client('s3')

def list_files():
    """
    Function to list files in a given S3 bucket
    """
    contents = dict()
    count = 0
    for item in s3.list_objects(Bucket=bucket_name)['Contents']:

        contents[count] = item
        count+=1
    return contents

def download_file(file_name):
    """
    Function to download a given file from an S3 bucket
    """
    output = f"downloads/{file_name}"
    s3.Bucket(bucket_name).download_file(file_name, output)

    return output

def mv_file(file_name, new_name):
        # Copy the old file to the new file location
    s3.copy_object(Bucket=bucket_name, CopySource={'Bucket': bucket_name, 'Key': file_name}, Key=new_name)

    # Delete the old file
    s3.delete_object(Bucket=bucket_name, Key=file_name)

def create_folder(folder_name):
    # Ensure the folder name ends with a slash
    if not folder_name.endswith('/'):
        folder_name += '/'
    s3.put_object(Bucket=bucket_name, Key=folder_name)

