import boto3

s3 = boto3.client("s3")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_BYTES = 15 * 1024 * 1024  # 15 MB safety cap


def lambda_handler(event, context):
    """First state in the workflow. Raising an exception here (instead of
    returning an error field) is what makes Step Functions' Catch block
    actually trigger — a normal return would be treated as success."""
    bucket = event["bucket"]
    key = event["key"]

    extension = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: .{extension}")

    head = s3.head_object(Bucket=bucket, Key=key)
    size_bytes = head["ContentLength"]
    if size_bytes > MAX_BYTES:
        raise ValueError(f"File too large: {size_bytes} bytes (limit is {MAX_BYTES})")

    print(f"Validated s3://{bucket}/{key} ({size_bytes} bytes, .{extension})")

    # Pass the original input forward, plus what this step learned
    event["validated"] = True
    event["original_size_bytes"] = size_bytes
    return event
