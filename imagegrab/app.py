import os
from types import new_class

from fastapi import FastAPI, UploadFile, File
import uuid
from minio import Minio
import redis
import io

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "images")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

@app.on_event("startup")
def startup():
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    new_path = f"{file_id}/original.jpg"

    data = await file.read()

    minio_client.put_object(
        MINIO_BUCKET,
        new_path,
        io.BytesIO(data),
        length=len(data),
        content_type="image/jpeg"
    )

    r.rpush("resize_queue", new_path)

    return {
        "status": "uploaded",
        "file": new_path
    }