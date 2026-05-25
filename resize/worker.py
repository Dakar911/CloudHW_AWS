import os
import cv2
import numpy as np
import redis
from minio import Minio
import io

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

while True:
    _, path = r.blpop("resize_queue")
    new_path = path.replace("original", "resize")
    print(f"[RESIZE] processing {new_path}")

    obj = minio_client.get_object(MINIO_BUCKET, path)
    data = obj.read()

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    h, w = image.shape[:2]
    resized = cv2.resize(image, (w // 2, h // 2))

    _, encoded = cv2.imencode('.jpg', resized)

    minio_client.put_object(
        MINIO_BUCKET,
        new_path,
        io.BytesIO(encoded.tobytes()),
        len(encoded.tobytes()),
        content_type="image/jpeg"
    )

    r.rpush("grayscale_queue", new_path)