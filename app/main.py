import os
import time
from typing import List, Dict, Any
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import DEFAULT_QUERY, INGEST_DAYS, RANGE_STEP
from .prometheus_adapter import fetch_range, to_series, fetch_instant, fetch_targets, fetch_metric_names
from .milvus_client import insert_segments, series_to_vector, search_similar
from .llm import analyze
from .alerts import send_wecom, send_dingtalk, send_email

app = FastAPI()
base_dir = os.path.dirname(os.path.dirname(__file__))
web_dir = os.path.join(base_dir, "web")
static_dir = os.path.join(web_dir, "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

last_analysis: Dict[str, Any] = {}

@app.get("/")
def index():
    path = os.path.join(web_dir, "index.html")
    return FileResponse(path)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest")
def ingest(metric: str = Query(DEFAULT_QUERY), step: str = Query(RANGE_STEP), demo: int = Query(0)):
    try:
        end_ts = int(time.time())
        start_ts = end_ts - INGEST_DAYS * 24 * 3600
        res = fetch_range(metric, start_ts, end_ts, step)
        series = to_series(res)
        segments: List[List[Any]] = []
        for _, points in series:
            if not points:
                continue
            win = 3600
            seg = []
            s = points[0][0]
            for ts, val in points:
                if ts - s <= win:
                    seg.append((ts, val))
                else:
                    if len(seg) >= 4:
                        segments.append(seg)
                    seg = [(ts, val)]
                    s = ts
            if len(seg) >= 4:
                segments.append(seg)
        try:
            count = insert_segments(metric, segments)
        except Exception as e2:
            return JSONResponse({"ok": False, "error": str(e2), "milvus_unavailable": True, "inserted": 0}, status_code=500)
        return {"inserted": count}
    except Exception as e:
        if demo == 1:
            now = int(time.time())
            segments = []
            for i in range(24):
                seg = []
                base = now - i * 3600
                for j in range(60):
                    ts = base - j * 60
                    val = 0.5 + 0.4 * (j % 10) / 10.0
                    if i % 7 == 0 and 20 < j < 30:
                        val += 1.0
                    seg.append((ts, val))
                segments.append(list(reversed(seg)))
            try:
                count = insert_segments(metric, segments)
                return {"inserted": count, "demo": True}
            except Exception as e2:
                return JSONResponse({"ok": False, "error": str(e2), "milvus_unavailable": True, "inserted": 0, "demo": True}, status_code=500)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

from .config import HOST_MAPPING

def get_env_info(metric_labels: Dict[str, str]) -> Dict[str, str]:
    # Extract instance or ip
    instance = metric_labels.get("instance", "")
    # Try exact match first
    if instance in HOST_MAPPING:
        return HOST_MAPPING[instance]
    
    # Try matching IP part if port is included
    ip = instance.split(":")[0]
    if ip in HOST_MAPPING:
        return HOST_MAPPING[ip]
        
    return {"env": "未知环境", "service": instance}

@app.get("/targets")
async def get_targets(instance: str = Query(None)):
    """List Prometheus targets and common metrics, optionally filtered by instance"""
    targets = []
    if not instance:
        targets = fetch_targets()
    metrics = fetch_metric_names(instance)
    return {"targets": targets, "metrics": metrics}

@app.get("/analyze")
async def analyze_metric(metric: str = Query(DEFAULT_QUERY), step: str = Query(RANGE_STEP), demo: int = Query(0)):
    """
    1. Fetch recent data from Prometheus
    2. Search similar history in Milvus
    3. LLM analysis
    """
    if demo:
        # Mock data for demo
        recent_points = [(int(time.time()) - i*60, 50 + i*0.1 + (10 if i>10 else 0)) for i in range(60)]
        context = []
        env_info = {"env": "测试环境", "service": "演示服务"}
        result = analyze(metric, recent_points, context, env_info)
        return result

    end_ts = int(time.time())
    start_ts = end_ts - 3600 * 6  # Last 6 hours
    
    res = fetch_range(metric, start_ts, end_ts, step)
    series = to_series(res)
    if not series:
        return {"error": "No data found for metric"}
    
    # Analyze the first series found
    metric_labels, recent_points = series[0]
    
    # Vector search context
    vec = series_to_vector(recent_points)
    vectors = search_similar(vec, top_k=3)
    context = []
    for v in vectors:
        # Fetch actual points for context
        c_res = fetch_range(v["metric_name"], v["start_ts"], v["end_ts"], step)
        ctx_series = to_series(c_res)
        if ctx_series:
            context.append({
                "metric_name": v["metric_name"],
                "start_ts": v["start_ts"],
                "end_ts": v["end_ts"],
                "distance": v["distance"]
            })
            
    # Resolve Environment and Service info
    env_info = get_env_info(metric_labels)

    result = analyze(metric, recent_points, context, env_info)
    
    # Inject recent points for visualization
    result["recent_points"] = recent_points
    return result

@app.post("/alert")
async def trigger_alert(metric: str = Query(DEFAULT_QUERY)):
    # Reuse analyze logic
    res = await analyze_metric(metric, step=RANGE_STEP, demo=0)
    if "error" in res:
        return res
        
    # Format message based on LLM result
    title = res.get("title", "告警分析")
    level = res.get("level", "未知")
    status = res.get("current_status", "")
    baseline = res.get("baseline", "")
    analysis = res.get("analysis", "")
    action = res.get("action", "")
    
    msg = (
        f"{title}\n"
        f"级别: {level}\n"
        f"状态: {status}\n"
        f"分析: {analysis}\n"
        f"建议: {action}"
    )
    
    # Send alerts
    sent_wecom = send_wecom(msg)
    sent_ding = send_dingtalk(msg)
    sent_email = send_email(f"AIOps Alert: {title}", msg)
    
    return {
        "analysis": res,
        "alerts_sent": {
            "wecom": sent_wecom,
            "dingtalk": sent_ding,
            "email": sent_email
        }
    }
