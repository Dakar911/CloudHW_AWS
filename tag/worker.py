import os
import cv2
import redis
import json
import numpy as np
import io
from minio import Minio

COLORS = np.random.uniform(0, 255, size=(21, 3))

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
    _, msg = r.blpop("tag_queue")

    job = json.loads(msg)

    path = job["image"]
    metadata_path = job["metadata"]

    print(f"[TAG] processing {path}")

    obj = minio_client.get_object(MINIO_BUCKET, path)
    data = obj.read()

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    metadata_obj = minio_client.get_object(MINIO_BUCKET, metadata_path)
    metadata = json.loads(metadata_obj.read())

    for idx, item in enumerate(metadata):
        color = COLORS[idx % len(COLORS)]

        cv2.rectangle(
            image,
            (item["startX"], item["startY"]),
            (item["endX"], item["endY"]),
            color,
            2
        )

        cv2.putText(
            image,
            item["label"],
            (item["startX"], item["startY"] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2
        )

    final_path = f"final-{path}"

    _, encoded = cv2.imencode('.jpg', image)
    encoded_bytes = encoded.tobytes()

    minio_client.put_object(
        MINIO_BUCKET,
        final_path,
        io.BytesIO(encoded_bytes),
        len(encoded_bytes),
        content_type="image/jpeg"
    )

    print(f"[TAG] final image saved: {final_path}")