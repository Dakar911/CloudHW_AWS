import cv2
import redis
import json
import numpy as np
import io
from minio import Minio

COLORS = np.random.uniform(0, 255, size=(21, 3))

r = redis.Redis(host="redis", port=6379, decode_responses=True)

minio_client = Minio(
    "minio:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

BUCKET = "images"

while True:
    _, msg = r.blpop("tag_queue")

    job = json.loads(msg)

    path = job["image"]
    metadata_path = job["metadata"]

    print(f"[TAG] processing {path}")

    obj = minio_client.get_object(BUCKET, path)
    data = obj.read()

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    metadata_obj = minio_client.get_object(BUCKET, metadata_path)
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
        BUCKET,
        final_path,
        io.BytesIO(encoded_bytes),
        len(encoded_bytes),
        content_type="image/jpeg"
    )

    print(f"[TAG] final image saved: {final_path}")