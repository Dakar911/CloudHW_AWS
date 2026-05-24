import cv2
import numpy as np
import redis
from minio import Minio
import io

r = redis.Redis(host="redis", port=6379, decode_responses=True)

minio_client = Minio(
    "minio:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

BUCKET = "images"

while True:
    _, path = r.blpop("resize_queue")

    print(f"[RESIZE] processing {path}")

    obj = minio_client.get_object(BUCKET, path)
    data = obj.read()

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    h, w = image.shape[:2]
    resized = cv2.resize(image, (w // 2, h // 2))

    _, encoded = cv2.imencode('.jpg', resized)

    minio_client.put_object(
        BUCKET,
        path,
        io.BytesIO(encoded.tobytes()),
        len(encoded.tobytes()),
        content_type="image/jpeg"
    )

    r.rpush("grayscale_queue", path)