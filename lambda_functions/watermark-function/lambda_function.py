import os
import boto3
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

s3 = boto3.client("s3")

DEST_BUCKET = os.environ["DEST_BUCKET"]
WATERMARK_TEXT = os.environ.get("WATERMARK_TEXT", "Alrasheed")


def lambda_handler(event, context):
    """Third state. Picks up the intermediate file the Resize step left
    behind, watermarks it, writes the FINAL result to the real destination
    key (no tmp/ prefix), then deletes the intermediate so it doesn't
    linger in the bucket."""
    tmp_bucket = event["tmp_bucket"]
    tmp_key = event["tmp_key"]
    final_key = event["key"]  # same filename as the original upload

    obj = s3.get_object(Bucket=tmp_bucket, Key=tmp_key)
    img = Image.open(BytesIO(obj["Body"].read())).convert("RGBA")

    watermark_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark_layer)

    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DejaVuSans-Bold.ttf")
    font_size = max(24, img.width // 15)
    try:
        font = ImageFont.truetype(font_path, size=font_size)
    except OSError:
        print(f"WARNING: could not load bundled font at {font_path}, falling back to default")
        font = ImageFont.load_default()

    text_bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    margin = 12
    position = (img.width - text_w - margin, img.height - text_h - margin)

    box_padding = 6
    draw.rectangle(
        [
            position[0] - box_padding,
            position[1] - box_padding,
            position[0] + text_w + box_padding,
            position[1] + text_h + box_padding,
        ],
        fill=(0, 0, 0, 110),
    )
    draw.text(position, WATERMARK_TEXT, font=font, fill=(255, 255, 255, 230))

    final_img = Image.alpha_composite(img, watermark_layer).convert("RGB")
    output_buffer = BytesIO()
    final_img.save(output_buffer, format="JPEG", quality=85)
    output_buffer.seek(0)

    s3.put_object(Bucket=DEST_BUCKET, Key=final_key, Body=output_buffer, ContentType="image/jpeg")
    s3.delete_object(Bucket=tmp_bucket, Key=tmp_key)  # clean up the intermediate

    print(f"Wrote final watermarked image to s3://{DEST_BUCKET}/{final_key}")

    event["dest_bucket"] = DEST_BUCKET
    event["dest_key"] = final_key
    return event
