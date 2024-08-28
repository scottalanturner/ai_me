import boto3
import time
import json
import logging
import argparse
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger(__name__)


def copy_to_s3(s3_client, local_file: str, bucket: str, object_name: str, override=False):
    print(f'Uploading {local_file} to s3://{bucket}/{object_name}')
    try:
        s3_client.upload_file(Filename=local_file, Bucket=bucket, Key=object_name)
    except ClientError as e:
        logging.error(3)
        return False
    return True

def start_job(
    job_name: str, 
    media_uri: str, 
    media_format: str,
    transcribe_client: boto3.client,
    output_key: str,
    output_bucket: str
):
    try:
        job = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": media_uri},
            MediaFormat=media_format,
            LanguageCode="en-US",
            OutputBucketName=output_bucket,
            OutputKey=output_key
        )
        logger.info(f"Started transcription job {job_name} for {media_uri}")
    except Exception as e:
        logger.exception(f"Couldn't start transcription job {job_name} for {media_uri}: {e}")
        raise
    else:
        return job

def transcribe_mp3(input_file_name: str, customer_id: str, upload_to_s3: bool = False):
    """ Connect to Amazon Transcribe and transcribe an MP3 file"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: $(message)s")

    s3_resource = boto3.resource("s3")
    s3_client = boto3.client("s3")
    transcribe_client = boto3.client("transcribe")

    object_name = None
    media_uri = None
    output_key = None
    output_bucket = None

    if (upload_to_s3):
        print(f"Creating bucket {customer_id} in region {transcribe_client.meta.region_name}.")

        bucket = s3_resource.create_bucket(
            Bucket=customer_id
        )
        media_file_name = f"media/{input_file_name}"
        media_object_key = input_file_name
        transcribe_key = f"{customer_id}/transcribe/{input_file_name}.json"

        # full path on s3
        object_name = f"{customer_id}/media/{media_object_key}"
        copy_to_s3(s3_client, local_file=media_file_name, bucket=customer_id, object_name=object_name)
        media_uri = f"s3://{bucket.name}/{object_name}"
    else:
        output_key = f"{customer_id}/transcribe/{input_file_name}.json"
        output_bucket = 'sat-aime-client'
        media_uri = f"s3://sat-aime-client/{customer_id}/media/{input_file_name}"


    job_name = f"{customer_id}-{int(time.time())}"
    print(f"Starting transcription job {job_name}")
    print(f"Media URI: {media_uri}")
    print(f"Output Key: {output_key}")
    print(f"Output Bucket: {output_bucket}")

    # Start the transcription job
    start_job(job_name=job_name, 
              media_uri=media_uri, 
              media_format="mp4", 
              transcribe_client=transcribe_client,
              output_key=output_key,
              output_bucket=output_bucket)

    # Wait for the job to complete
    while True:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        print("Waiting for transcription job to complete...")
        time.sleep(10)
    
    if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        print("Transcription job completed successfully.")
        transcript_file_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        print(f'Transcript: {transcript_file_uri}')  
        # Upload the transcription to S3 where it can be worked on by other services
        return status['TranscriptionJob']['Transcript']['TranscriptFileUri']
    else:
        failure_reason = status['TranscriptionJob']['FailureReason']
        logger.exception(f"Transcription job failed: {failure_reason}")
        raise Exception("Transcription job failed.")

if __name__ == "__main__":
    #parser = argparse.ArgumentParser(description="Transcribe an MP3 file using Amazon Transcribe")
    #parser.add_argument("bucket_root", help="The name of the S3 bucket to create", type=str)
    #parser.add_argument("input file name", help="The name of the media file to transcribe", type=str)
    #args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    transcribe_mp3(customer_id="aaron", input_file_name="ISI2024Keynote.mp4")