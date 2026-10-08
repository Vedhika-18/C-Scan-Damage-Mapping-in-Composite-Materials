import os
import shutil
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent.parent
LOCAL_OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(ROOT / "outputs")))
S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")


def is_remote() -> bool:
    return bool(S3_BUCKET)


def _client():
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET is required for object storage.")
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("Install boto3 to use object storage.") from exc
    return boto3.client(
        "s3",
        region_name=S3_REGION,
        endpoint_url=S3_ENDPOINT_URL or None,
    )


def upload_file(path: str | Path, key: str, content_type: str) -> str:
    path = Path(path)
    if is_remote():
        _client().upload_file(
            str(path),
            S3_BUCKET,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return key
    destination = LOCAL_OUTPUT_DIR / key
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)
    return str(destination)


def public_url(key: str) -> str:
    if not is_remote():
        return f"/api/files/{quote(key)}"
    if S3_ENDPOINT_URL:
        return _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=3600,
        )
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600,
    )


def download_local(key: str) -> Path | None:
    if is_remote():
        return None
    path = LOCAL_OUTPUT_DIR / key
    return path if path.is_file() else None
