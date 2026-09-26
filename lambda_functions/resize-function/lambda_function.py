import os
import boto3
from io import BytesIO
from PIL import Image

s3 = boto3.client("s3")

DEST_BUCKET = os.environ["DEST_BUCKET"]
MAX_DIMENSION = 800


def lambda_handler(event, context):
    """Second state. Step Functions payloads are capped at 256KB, so we
    can't pass raw image bytes between states — instead this step writes
    an intermediate file to S3 and passes forward a POINTER (bucket+key)
    for the next step to pick up. Same idea as a relay race: pass the
    location of the baton, not the baton itself."""
    bucket = event["bucket"]
    key = event["key"]

    obj = s3.get_object(Bucket=bucket, Key=key)
    img = Image.open(BytesIO(obj["Body"].read())).convert("RGBA")
    original_size = img.size

    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))  # only ever shrinks

    # PNG here (not JPEG) to avoid a lossy round-trip before the watermark
    # step does the final JPEG save.
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    tmp_key = f"tmp/{key}.png"
    s3.put_object(Bucket=DEST_BUCKET, Key=tmp_key, Body=buffer, ContentType="image/png")

    print(f"Resized {original_size} -> {img.size}, wrote intermediate to s3://{DEST_BUCKET}/{tmp_key}")

    event["tmp_bucket"] = DEST_BUCKET
    event["tmp_key"] = tmp_key
    event["original_width"], event["original_height"] = original_size
    event["resized_width"], event["resized_height"] = img.size
    return event
