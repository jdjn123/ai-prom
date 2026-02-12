import os
import yaml

# Load config.yaml
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
except FileNotFoundError:
    print(f"Warning: {CONFIG_PATH} not found, using defaults.")
    config_data = {}

def get_cfg(section, key, default):
    return config_data.get(section, {}).get(key, default)

# Prometheus
PROMETHEUS_URL = get_cfg("prometheus", "url", os.environ.get("PROMETHEUS_URL", "http://localhost:9090"))
DEFAULT_QUERY = get_cfg("prometheus", "default_query", os.environ.get("DEFAULT_QUERY", "up"))
RANGE_STEP = get_cfg("prometheus", "range_step", os.environ.get("RANGE_STEP", "60s"))
INGEST_DAYS = int(get_cfg("prometheus", "ingest_days", os.environ.get("INGEST_DAYS", "15")))

# Host Mapping
HOST_MAPPING = config_data.get("hosts", {})

# Milvus
MILVUS_HOST = get_cfg("milvus", "host", os.environ.get("MILVUS_HOST", "127.0.0.1"))
MILVUS_PORT = int(get_cfg("milvus", "port", os.environ.get("MILVUS_PORT", "19530")))
MILVUS_COLLECTION = get_cfg("milvus", "collection_name", "metric_series")

# Ollama
OLLAMA_HOST = get_cfg("ollama", "host", os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
OLLAMA_MODEL = get_cfg("ollama", "model", os.environ.get("OLLAMA_MODEL", "qwen2:latest"))

# Alerts - WeCom
WECOM_ENABLED = config_data.get("alerts", {}).get("wecom", {}).get("enabled", False)
WECOM_WEBHOOK = config_data.get("alerts", {}).get("wecom", {}).get("webhook", os.environ.get("WECOM_WEBHOOK", ""))

# Alerts - DingTalk
DINGTALK_ENABLED = config_data.get("alerts", {}).get("dingtalk", {}).get("enabled", False)
DINGTALK_WEBHOOK = config_data.get("alerts", {}).get("dingtalk", {}).get("webhook", os.environ.get("DINGTALK_WEBHOOK", ""))

# Alerts - Email
EMAIL_ENABLED = config_data.get("alerts", {}).get("email", {}).get("enabled", False)
SMTP_HOST = config_data.get("alerts", {}).get("email", {}).get("smtp_host", os.environ.get("SMTP_HOST", ""))
SMTP_PORT = int(config_data.get("alerts", {}).get("email", {}).get("smtp_port", os.environ.get("SMTP_PORT", "587")))
SMTP_USER = config_data.get("alerts", {}).get("email", {}).get("smtp_user", os.environ.get("SMTP_USER", ""))
SMTP_PASS = config_data.get("alerts", {}).get("email", {}).get("smtp_pass", os.environ.get("SMTP_PASS", ""))
MAIL_TO = config_data.get("alerts", {}).get("email", {}).get("mail_to", os.environ.get("MAIL_TO", ""))
