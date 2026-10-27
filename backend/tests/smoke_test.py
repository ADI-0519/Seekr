import io
import os
import time
import uuid

import pika
import psycopg2
import pytest
import qdrant_client
import redis
from minio import Minio
from minio.error import S3Error

from tests.test_tasks import ping

pytestmark = pytest.mark.integration


# Smoke tests for service connectivity
def test_postgres_connect():
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "SeekrDB"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
    )

    cur = conn.cursor()
    cur.execute("SELECT 1;")
    assert cur.fetchone()[0] == 1
    cur.close()
    conn.close()


# Smoke test for Qdrant connectivity
def test_qdrant_connect():
    client = qdrant_client.QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333)),
        # Avoid version warning
        prefer_grpc=False,
        timeout=3,
        api_key=None,
        https=False,
        check_compatibility=False,
    )

    collection = f"smoke_{uuid.uuid4().hex[:8]}"

    try:
        client.create_collection(
            collection_name=collection,
            vectors_config=qdrant_client.http.models.VectorParams(
                size=3, distance=qdrant_client.http.models.Distance.COSINE
            ),
        )
        client.upsert(
            collection_name=collection,
            points=[
                qdrant_client.http.models.PointStruct(
                    id=1, vector=[0.1, 0.2, 0.3], payload={"tag": "smoke"}
                )
            ],
        )
        if hasattr(client, "search"):
            results = client.search(
                collection_name=collection, query_vector=[0.1, 0.2, 0.3], limit=1
            )
        elif hasattr(client, "search_points"):
            results = client.search_points(
                collection_name=collection, query_vector=[0.1, 0.2, 0.3], limit=1
            )
        else:
            results = client.query_points(
                collection_name=collection, query=[0.1, 0.2, 0.3], limit=1
            ).points
        assert len(results) == 1
    finally:
        client.delete_collection(collection_name=collection)


# Smoke test for Redis connectivity
def test_redis_connect():
    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", 6379)), db=0
    )
    pong = r.ping()
    assert pong is True
    r.set("smoke_key", "smoke_value")
    assert r.get("smoke_key") == b"smoke_value"
    r.delete("smoke_key")


# Smoke test for RabbitMQ connectivity
def test_rabbitmq_connect():
    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_DEFAULT_USER", "guest"), os.getenv("RABBITMQ_DEFAULT_PASS", "guest")
    )

    params = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "localhost"),
        port=int(os.getenv("RABBITMQ_PORT", 5672)),
        credentials=credentials,
    )

    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue="test_queue", durable=False)
    channel.basic_publish(exchange="", routing_key="test_queue", body="test")
    method_frame, header_frame, body = channel.basic_get("test_queue")
    assert body == b"test"
    channel.queue_delete(queue="test_queue")
    connection.close()


# Celery smoke test
def test_celery_connect():
    result = ping.delay()
    for _ in range(20):
        if result.ready():
            break
        time.sleep(0.5)
    assert result.ready(), "Celery task did not complete in time"
    assert result.result == "pong"


# Smoke test for MinIO connectivity
def test_minio_connect():
    endpoint = os.getenv("MINIO_HOST")
    if not endpoint:
        endpoint_url = os.getenv("STORAGE_ENDPOINT_URL", "http://localhost:9000")
        endpoint = endpoint_url.replace("http://", "").replace("https://", "")
        if endpoint.startswith("minio:"):
            endpoint = endpoint.replace("minio:", "localhost:", 1)
    primary_access = (
        os.getenv("MINIO_ROOT_USER") or os.getenv("STORAGE_ACCESS_KEY_ID") or "minioadmin"
    )
    primary_secret = (
        os.getenv("MINIO_ROOT_PASSWORD") or os.getenv("STORAGE_SECRET_ACCESS_KEY") or "minioadmin"
    )
    fallback_access = "minioadmin"
    fallback_secret = "minioadmin"

    bucket = f"smoke-{uuid.uuid4().hex[:8]}"
    for access_key, secret_key in [
        (primary_access, primary_secret),
        (fallback_access, fallback_secret),
    ]:
        try:
            client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False,
            )
            object_name = f"test-{uuid.uuid4().hex[:8]}.txt"
            try:
                if not client.bucket_exists(bucket):
                    client.make_bucket(bucket)
                data_bytes = io.BytesIO(b"hello")
                client.put_object(bucket, object_name, data=data_bytes, length=5)
                data = client.get_object(bucket, object_name).read()
                assert data == b"hello"
                return
            finally:
                try:
                    client.remove_object(bucket, object_name)
                except S3Error:
                    pass
                try:
                    client.remove_bucket(bucket)
                except S3Error:
                    pass
        except S3Error as exc:
            if exc.code not in ("InvalidAccessKeyId", "SignatureDoesNotMatch"):
                raise
    raise AssertionError("MinIO credentials did not match running instance.  ")
