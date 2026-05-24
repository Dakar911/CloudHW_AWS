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
    _, path = r.blpop("grayscale_queue")

    print(f"[GRAYSCALE] processing {path}")

    obj = minio_client.get_object(BUCKET, path)
    data = obj.read()

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    _, encoded = cv2.imencode('.jpg', gray)

    minio_client.put_object(
        BUCKET,
        path,
        io.BytesIO(encoded.tobytes()),
        len(encoded.tobytes()),
        content_type="image/jpeg"
    )

    r.rpush("detect_queue", path)