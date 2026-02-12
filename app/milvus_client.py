from typing import List, Tuple, Dict, Any
import numpy as np
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from .config import MILVUS_HOST, MILVUS_PORT

COLLECTION_NAME = "metrics_segments"
DIM = 128

def connect():
    try:
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
    except Exception:
        connections.disconnect(alias="default")
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)

def ensure_collection() -> Collection:
    if not utility.has_collection(COLLECTION_NAME):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="metric_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="start_ts", dtype=DataType.INT64),
            FieldSchema(name="end_ts", dtype=DataType.INT64),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=DIM),
        ]
        schema = CollectionSchema(fields=fields, description="Prometheus metric segments")
        col = Collection(name=COLLECTION_NAME, schema=schema)
        col.create_index(field_name="vector", index_params={"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 1024}})
        col.load()
        return col
    col = Collection(COLLECTION_NAME)
    col.load()
    return col

def series_to_vector(points: List[Tuple[int, float]], dim: int = DIM) -> List[float]:
    if not points:
        return [0.0] * dim
    points = sorted(points, key=lambda x: x[0])
    xs = np.array([p[0] for p in points], dtype=np.float64)
    ys = np.array([p[1] for p in points], dtype=np.float64)
    if xs.max() == xs.min():
        return [float(ys.mean())] * dim
    xs = (xs - xs.min()) / (xs.max() - xs.min() + 1e-9)
    target = np.linspace(0.0, 1.0, dim)
    vec = np.interp(target, xs, ys)
    mu = vec.mean()
    sigma = vec.std() + 1e-9
    vec = (vec - mu) / sigma
    return vec.astype(np.float32).tolist()

def insert_segments(metric_name: str, segments: List[List[Tuple[int, float]]]) -> int:
    connect()
    col = ensure_collection()
    if not segments:
        return 0
    vectors = [series_to_vector(seg) for seg in segments]
    start_ts = [seg[0][0] if seg else 0 for seg in segments]
    end_ts = [seg[-1][0] if seg else 0 for seg in segments]
    metric_names = [metric_name] * len(segments)
    col.insert([metric_names, start_ts, end_ts, vectors])
    col.flush()
    return len(segments)

def search_similar(vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    connect()
    col = ensure_collection()
    res = col.search(data=[vector], anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 16}}, limit=top_k, output_fields=["metric_name", "start_ts", "end_ts"])
    hits = []
    for h in res[0]:
        hits.append({
            "metric_name": h.entity.get("metric_name"),
            "start_ts": h.entity.get("start_ts"),
            "end_ts": h.entity.get("end_ts"),
            "distance": float(h.distance)
        })
    return hits
