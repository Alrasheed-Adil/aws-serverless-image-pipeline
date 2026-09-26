import json
import os
import boto3

sfn = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]


def lambda_handler(event, context):
    """SQS-triggered, same as the old image-processor was. Instead of
    doing the work itself, this just unpacks the S3 event and hands it
    off to the state machine as a fresh execution."""
    for sqs_record in event["Records"]:
        s3_event = json.loads(sqs_record["body"])

        if "Records" not in s3_event:
            print("Skipping non-S3 message (likely the S3 test event)")
            continue

        for s3_record in s3_event["Records"]:
            bucket = s3_record["s3"]["bucket"]["name"]
            key = s3_record["s3"]["object"]["key"]

            execution_input = {"bucket": bucket, "key": key}
            response = sfn.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                input=json.dumps(execution_input),
            )
            print(f"Started execution {response['executionArn']} for s3://{bucket}/{key}")

    return {"statusCode": 200}
