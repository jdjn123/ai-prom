import json
from typing import List, Tuple, Dict, Any
import requests
from .config import OLLAMA_HOST, OLLAMA_MODEL

def call_llm(prompt: str) -> str:
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    r = requests.post(
        url,
        json=payload,
        timeout=300  # 增加超时时间到 5 分钟，防止大模型响应慢
    )
    r.raise_for_status()
    data = r.json()
    return data.get("response", "")

def build_prompt(metric_name: str, recent_points: List[Tuple[int, float]], context: List[Dict[str, Any]], env_info: Dict[str, str]) -> str:
    pts = [{"ts": ts, "val": val} for ts, val in recent_points[-200:]]
    ctx = [{"metric_name": c.get("metric_name"), "start_ts": c.get("start_ts"), "end_ts": c.get("end_ts"), "distance": c.get("distance")} for c in context]
    
    env_str = f"环境: {env_info.get('env', '未知环境')}\n服务: {env_info.get('service', '未知服务')}"
    
    prompt = (
        "你是SRE告警分析助手。基于Prometheus指标进行异常识别、趋势预测和根因推断。\n"
        f"指标: {metric_name}\n"
        f"{env_str}\n"
        f"最近数据点(JSON): {json.dumps(pts, ensure_ascii=False)}\n"
        f"相似历史片段(JSON): {json.dumps(ctx, ensure_ascii=False)}\n"
        "请返回JSON格式，内容言简意赅，不要啰嗦:\n"
        "  - thought: 字符串，简要的分析思路。\n"
        "  - title: 字符串，简短的告警标题 (如 '【异常】订单服务内存飙升')。\n"
        "  - current_status: 字符串，仅描述当前值和状态。\n"
        "  - level: 字符串，异常级别 (如 '高风险', '中风险', '低风险', '正常')。\n"
        "  - prediction: 字符串，预测结论 (如 '预计10分钟后达到阈值')。\n"
        "  - prediction_points: 数组，预测未来5个点 [[ts, val], ...]，用于绘图。\n"
        "  - analysis: 字符串，核心原因分析。禁止罗列具体数据点坐标。\n"
        "  - action: 字符串，关键建议。\n"
        "不要包含 Markdown 代码块，直接返回 JSON。"
    )
    return prompt

def analyze(metric_name: str, recent_points: List[Tuple[int, float]], context: List[Dict[str, Any]], env_info: Dict[str, str] = None) -> Dict[str, Any]:
    if env_info is None:
        env_info = {}
    prompt = build_prompt(metric_name, recent_points, context, env_info)
    try:
        text = call_llm(prompt)
        # Clean up potential markdown code blocks
        clean_text = text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
            
        try:
            data = json.loads(clean_text)
            return data
        except Exception as e:
            print(f"JSON Parse Error: {e}, text: {text}")
            return {"title": "分析失败", "level": "未知", "thought": "解析JSON失败", "analysis": text}
    except Exception as e:
        print(f"LLM Call Error: {e}")
        vals = [v for _, v in recent_points[-200:]] if recent_points else []
        if not vals:
            return {"title": "数据缺失", "level": "未知", "thought": "无数据", "analysis": "无法获取数据"}
        
        # Fallback simple logic
        import numpy as np
        a = np.array(vals, dtype=np.float64)
        diff = float(a[-1] - a[0])
        trend = "上涨" if diff > 0.05 else "下降" if diff < -0.05 else "稳定"
        z = float((a[-1] - a.mean()) / (a.std() + 1e-9))
        is_anomaly = abs(z) > 2.0
        level = "中风险" if is_anomaly else "正常"
        
        return {
            "title": f"【系统降级】{metric_name} 统计分析",
            "current_status": f"当前值 {a[-1]:.2f}, 趋势 {trend}",
            "baseline": f"均值 {a.mean():.2f}",
            "level": level,
            "analysis": "LLM不可用，仅提供统计分析。",
            "action": "检查LLM服务状态",
            "thought": "LLM服务异常，降级处理"
        }
