import boto3

from config.config import S3_BUCKET


def create_presigned_url(key: str, expires_in: int = 300) -> str:
    s3 = boto3.client("s3")
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
