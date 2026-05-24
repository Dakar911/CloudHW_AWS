from fastapi import FastAPI, UploadFile, File
import uuid
from minio import Minio
import redis
import io

app = FastAPI()

r = redis.Redis(host="redis", port=6379, decode_responses=True)

minio_client = Minio(
    "minio:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

BUCKET = "images"


@app.on_event("startup")
def startup():
    if not minio_client.bucket_exists(BUCKET):
        minio_client.make_bucket(BUCKET)


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = f"{file_id}.jpg"

    data = await file.read()

    minio_client.put_object(
        BUCKET,
        file_path,
        io.BytesIO(data),
        length=len(data),
        content_type="image/jpeg"
    )

    r.rpush("resize_queue", file_path)

    return {
        "status": "uploaded",
        "file": file_path
    }