import s3_management as s3_management
import os
from watchtower import CloudWatchLogHandler
import time
import logging
import datetime
import platform
import ffmpeg
from dotenv import load_dotenv


internal_bucket = os.environ.get("INTERNAL_BUCKET_NAME")
logger = logging.getLogger(__name__)
load_dotenv()
timeobj = datetime.datetime.now()
cloud_watch_stream_name = "vacuum_flask_worker_log_{0}_{1}".format(platform.node(),timeobj.strftime("%Y%m%d%H%M%S"))
cloudwatch_handler = CloudWatchLogHandler(
    log_group_name='vacuum_flask',  # Replace with your desired log group name
    stream_name=cloud_watch_stream_name,  # Replace with a stream name
)
logger.addHandler(cloudwatch_handler)
logger.setLevel(logging.INFO)

def s3_watcher():
    files = s3_management.list_files(internal_bucket)
    for key,item in files.items():
        # key is the path/file in s3
        # item is the full object returned by s3
        if item["fileext"] == "mov":
            logger.info(f"Found a mov file {key}")
            remux_file(key, internal_bucket)
    logger.info("Sleeping 120 seconds.")
def remux_file(key, bucket):
    # Download the file from S3 to ElasticStorage
    download_path_key = s3_management.download_file(key, bucket)
    logger.info(f"Downloaded s3 {key} to {download_path_key}")
    # Convert the file
    # Use ffmpeg to remux the MOV to MP4
    new_file_name = download_path_key.replace(".mov",".mp4")
    logger.info("Starting remuxing")
    logger.info(f"Remuxing file {download_path_key} to new file {new_file_name}")
    try:
        (
            ffmpeg
            .input(download_path_key)
            .output(new_file_name, vcodec='libx264',
                    acodec='aac')  # Copy video and audio streams without re-encoding
            .run(quiet=True, overwrite_output=True)
        )
    except ffmpeg.Error as e:
        logger.error(f"Error during remuxing: {e.stderr.decode()}")
        raise
    logger.info("Finished remuxing")
    # Upload to the public bucket
    logger.info(f"Starting Upload {new_file_name} to S3 public bucket.")
    with open(new_file_name, "rb") as new_file:
        s3_management.s3_upload_file(new_file, os.path.basename(new_file_name))
    logging.info(f"Uploaded {new_file_name} to the public bucket.")
    # clean up files in elasticstorage
    os.remove(download_path_key)
    logger.info(f"Removed {download_path_key}.")
    os.remove(new_file_name)
    logger.info(f"Removed {new_file_name}.")
    # clean up internal s3 file
    s3_management.s3_remove_file(key, internal_bucket)
    logger.info(f"Removed {key} from {internal_bucket}.")
    logger.info(f"Finished remux of {key}.")
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting worker")
    s3_watcher()
