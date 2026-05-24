import os
import cv2
import numpy as np
from minio import Minio
import io
import json
import redis

CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow",
    "diningtable", "dog", "horse", "motorbike", "person",
    "pottedplant", "sheep", "sofa", "train", "tvmonitor"
]

CONFIDENCE_MIN = 0.4

net = cv2.dnn.readNetFromCaffe(
    "/app/MobileNetSSD_deploy.prototxt",
    "/app/MobileNetSSD_deploy.caffemodel"
)

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
    _, path = r.blpop("detect_queue")

    print(f"[DETECT] processing {path}")

    obj = minio_client.get_object(MINIO_BUCKET, path)
    data = obj.read()

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    h, w = image.shape[:2]

    blob = cv2.dnn.blobFromImage(image, 0.007843, (w, h), 127.5)

    net.setInput(blob)
    detections = net.forward()

    results = []

    for i in np.arange(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]

        if confidence > CONFIDENCE_MIN:
            idx = int(detections[0, 0, i, 1])

            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            results.append({
                "label": CLASSES[idx],
                "startX": int(startX),
                "startY": int(startY),
                "endX": int(endX),
                "endY": int(endY)
            })

    metadata_path = path.replace(".jpg", ".json")

    json_data = json.dumps(results).encode()

    minio_client.put_object(
        MINIO_BUCKET,
        metadata_path,
        io.BytesIO(json_data),
        len(json_data),
        content_type="application/json"
    )

    r.rpush("tag_queue", json.dumps({
        "image": path,
        "metadata": metadata_path
    }))