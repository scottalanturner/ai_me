import boto3
import json

def download_transcription_and_save_plain_text(bucket_name, json_key, local_text_file):
    # Initialize the S3 client
    s3_client = boto3.client('s3')
    
    # Download the JSON file from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=json_key)
    json_content = response['Body'].read().decode('utf-8')
    
    # Parse the JSON content
    transcription_result = json.loads(json_content)
    
    # Extract the plain text from the JSON
    plain_text = transcription_result['results']['transcripts'][0]['transcript']
    
    # Write the plain text to a local text file
    with open(local_text_file, 'w') as file:
        file.write(plain_text)

    print(f"Plain text transcription saved to {local_text_file}")

# Example usage:
# download_transcription_and_save_plain_text('your-bucket-name', 'path/to/your-transcription.json', 'transcription.txt')
download_transcription_and_save_plain_text(bucket_name='sat-aime-client',
                                           json_key='aaron/transcribe/ISIKeynote2023.mp4.json',
                                           local_text_file='ISI2023Keynote.txt')