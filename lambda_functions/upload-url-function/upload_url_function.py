import json
import os
import uuid
import boto3

s3 = boto3.client("s3")
SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
URL_EXPIRY_SECONDS = 300  # 5 minutes to actually perform the upload


def lambda_handler(event, context):
    """API Gateway (HTTP API) entry point. Returns a presigned URL the
    caller can PUT an image to directly — no AWS credentials needed on
    their end, which is the whole point of presigning."""

    query_params = event.get("queryStringParameters") or {}
    original_filename = query_params.get("filename", "upload.jpg")
    extension = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "jpg"

    # A random key avoids collisions between different uploaders and
    # avoids trusting user-supplied filenames as S3 keys directly.
    object_key = f"{uuid.uuid4()}.{extension}"

    presigned_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": SOURCE_BUCKET, "Key": object_key, "ContentType": "image/jpeg"},
        ExpiresIn=URL_EXPIRY_SECONDS,
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"upload_url": presigned_url, "object_key": object_key}),
    }
