import time
from typing import List, Dict, Any, Tuple
import requests
from .config import PROMETHEUS_URL

def parse_step(step: str) -> int:
    unit = step[-1]
    if unit.isdigit():
        return int(step)
    val = int(step[:-1])
    if unit == 's': return val
    if unit == 'm': return val * 60
    if unit == 'h': return val * 3600
    if unit == 'd': return val * 86400
    return val

def fetch_range(query: str, start_ts: int, end_ts: int, step: str) -> Dict[str, Any]:
    step_sec = parse_step(step)
    # Estimate points. If > 10000, chunk it. 
    # Prometheus often limits to 11000 points per series.
    total_points = (end_ts - start_ts) / step_sec
    
    if total_points <= 10000:
        params = {"query": query, "start": start_ts, "end": end_ts, "step": step}
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    
    # Chunking logic
    chunk_size = 10000 * step_sec
    # Align chunk_size to step to keep grid consistent (optional but good)
    chunk_size = (chunk_size // step_sec) * step_sec
    
    combined_results = {}
    
    curr = start_ts
    while curr < end_ts:
        next_ts = min(curr + chunk_size, end_ts)
        params = {"query": query, "start": curr, "end": next_ts, "step": step}
        try:
            r = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params=params, timeout=60)
            r.raise_for_status()
            data = r.json().get("data", {}).get("result", [])
            
            for item in data:
                # Create a unique key for the metric
                metric = item.get("metric", {})
                # Sort keys to ensure stable string representation
                key = str(sorted(metric.items()))
                
                if key not in combined_results:
                    combined_results[key] = item
                else:
                    # Merge values
                    existing = combined_results[key].get("values", [])
                    new_vals = item.get("values", [])
                    # Simple deduplication based on timestamp (first element)
                    if existing and new_vals:
                        last_ts = existing[-1][0]
                        for v in new_vals:
                            if v[0] > last_ts:
                                existing.append(v)
                    elif new_vals:
                         combined_results[key]["values"] = new_vals
                         
        except Exception as e:
            print(f"Error fetching chunk {curr}-{next_ts}: {e}")
            # Continue to next chunk to get partial data at least
        
        # Advance current time. 
        # To avoid overlap issues, we could start next from next_ts + step_sec
        # But simply using next_ts is safer if we handle deduplication.
        curr = next_ts
        
    return {
        "status": "success", 
        "data": {
            "resultType": "matrix",
            "result": list(combined_results.values())
        }
    }

def fetch_instant(query: str) -> Dict[str, Any]:
    params = {"query": query, "time": int(time.time())}
    r = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_targets() -> List[Dict[str, Any]]:
    """Fetch all active targets from Prometheus"""
    try:
        r = requests.get(f"{PROMETHEUS_URL}/api/v1/targets", timeout=15)
        r.raise_for_status()
        data = r.json().get("data", {}).get("activeTargets", [])
        return [
            {
                "instance": t.get("labels", {}).get("instance"),
                "job": t.get("labels", {}).get("job"),
                "health": t.get("health"),
                "lastScrape": t.get("lastScrape"),
                "labels": t.get("labels", {})
            }
            for t in data
        ]
    except Exception as e:
        print(f"Error fetching targets: {e}")
        return []

def fetch_metric_names(instance: str = None) -> List[str]:
    """Fetch metric names, optionally filtered by instance"""
    try:
        if instance:
            # Query: {instance="xxx"}
            # We want to find all metrics that have this instance label.
            # Using /api/v1/series is better but might be heavy.
            # Alternative: /api/v1/label/__name__/values?match[]={instance="xxx"}
            params = {"match[]": f'{{instance="{instance}"}}'}
            r = requests.get(f"{PROMETHEUS_URL}/api/v1/label/__name__/values", params=params, timeout=15)
            r.raise_for_status()
            return r.json().get("data", [])
        
        # Default common metrics
        return [
            "up",
            "node_load1",
            "node_load5",
            "node_load15",
            "node_memory_MemAvailable_bytes",
            "node_memory_MemTotal_bytes",
            "node_cpu_seconds_total",
            "node_filesystem_avail_bytes",
            "node_network_receive_bytes_total",
            "node_network_transmit_bytes_total",
            "process_resident_memory_bytes",
            "go_goroutines"
        ]
    except Exception as e:
        print(f"Error fetching metrics for {instance}: {e}")
        return []

def to_series(result: Dict[str, Any]) -> List[Tuple[Dict[str, str], List[Tuple[int, float]]]]:
    data = result.get("data", {}).get("result", [])
    series = []
    for item in data:
        metric = item.get("metric", {})
        values = item.get("values", []) or item.get("value", [])
        points = []
        for v in values:
            if isinstance(v, list) and len(v) >= 2:
                ts = int(float(v[0]))
                val = float(v[1])
                points.append((ts, val))
            elif isinstance(values, list) and len(values) == 2:
                ts = int(float(values[0]))
                val = float(values[1])
                points.append((ts, val))
                break
        series.append((metric, points))
    return series
