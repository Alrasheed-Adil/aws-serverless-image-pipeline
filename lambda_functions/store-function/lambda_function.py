import os
import time
import boto3

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = os.environ["TABLE_NAME"]
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """Final state. This is the only step that touches DynamoDB/SNS,
    matching least-privilege: the resize/watermark functions have no
    reason to hold those permissions at all."""
    image_id = event["key"]

    item = {
        "image_id": image_id,
        "status": "processed",
        "processed_at": int(time.time()),
        "original_width": event.get("original_width"),
        "original_height": event.get("original_height"),
        "resized_width": event.get("resized_width"),
        "resized_height": event.get("resized_height"),
    }
    table.put_item(Item=item)
    print(f"Wrote metadata for {image_id}")

    if SNS_TOPIC_ARN:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Image processed successfully",
            Message=(
                f"{image_id}: {event.get('original_width')}x{event.get('original_height')} "
                f"-> {event.get('resized_width')}x{event.get('resized_height')}, "
                f"stored at s3://{event.get('dest_bucket')}/{event.get('dest_key')}"
            ),
        )

    event["status"] = "processed"
    return event
