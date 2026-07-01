import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# 1. Initialize the S3 client with your credentials
s3_client = boto3.client(
    's3',
    endpoint_url="https://s3.gamana.cloud",
    aws_access_key_id="goldeneyelocal",
    aws_secret_access_key="MnbbnUOV64KdFmA",
    region_name="ap-south-1",
    # Forces path-style (s3.gamana.cloud/bucket) instead of virtual-host (bucket.s3.gamana.cloud)
    config=Config(s3={'addressing_style': 'path'})
)

bucket_name = "camera-feeds-local"

# 2. Test the connection by listing files in the bucket
try:
    print(f"Attempting to connect to bucket '{bucket_name}'...")
    
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    
    print("\n✅ Connection Successful!")
    
    if 'Contents' in response:
        print("Files currently in the bucket:")
        for item in response['Contents']:
            print(f" - {item['Key']} ({item['Size']} bytes)")
    else:
        print("The bucket is connected but currently empty.")

except ClientError as e:
    error_code = e.response['Error']['Code']
    print(f"\n❌ Server Error: {e}")
    
    # Helpful pointers depending on what the server returns
    if error_code == 'InvalidAccessKeyId':
        print("👉 Tip: The server rejected 'goldeneyelocal'. Double-check if the keys are still active on the server console.")
    elif error_code == 'NoSuchBucket':
        print(f"👉 Tip: Authenticated successfully, but the bucket '{bucket_name}' doesn't exist.")

except Exception as e:
    print(f"\n❌ Network or Connection Error: {e}")
    print("👉 Tip: Check your internet connection or verify if https://s3.gamana.cloud is online.")