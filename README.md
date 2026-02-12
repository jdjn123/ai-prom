# AI-Prom

AI-Prom 是一个智能化的 Prometheus 监控指标分析工具。它结合了 Prometheus 监控数据、Milvus 向量数据库和 LLM（大语言模型），提供指标数据的自动摄取、异常检测、相似性搜索以及智能分析功能。（用的1.7b的ai，看上去不是很聪明，建议使用30b以上）
<img width="725" height="730" alt="1770868249277" src="https://github.com/user-attachments/assets/64d37b44-e43e-4cea-8caf-0e2b9fb7fa75" />
<img width="725" height="730" alt="1770868249277" src="https://github.com/user-attachments/assets/64d37b44-e43e-4cea-8caf-0e2b9fb7fa75" />
<img width="1468" height="2066" alt="image" src="https://github.com/user-attachments/assets/c08bbf40-d89b-4640-9f7e-c67f4ad25873" />




## 主要功能

*   **数据摄取**: 从 Prometheus 自动拉取历史指标数据。
*   **向量存储**: 将时间序列数据转化为向量并存储到 Milvus 数据库，支持高效的相似性检索。
*   **智能分析**: 利用 LLM (通过 Ollama 集成) 对监控指标进行深度分析，识别潜在问题。
*   **告警通知**: 支持钉钉、企业微信和邮件告警，及时通知异常情况。
*   **Web 界面**: 提供直观的 Web 界面进行操作和结果展示。

## 技术栈

*   **后端**: Python, FastAPI
*   **前端**: HTML, JavaScript, CSS
*   **数据存储**: Prometheus (数据源), Milvus (向量存储)
*   **AI 模型**: Ollama (支持 Qwen 等模型)

## 快速开始

### 1. 环境准备

确保你已经安装了 Python 3.8+，并且可以访问以下服务：
*   Prometheus
*   Milvus
*   Ollama

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置文件

修改根目录下的 `config.yaml` 文件，配置相关服务地址和参数：

```yaml
prometheus:
  url: "http://your-prometheus-host:9090"
  # ...

milvus:
  host: "your-milvus-host"
  # ...

ollama:
  host: "http://your-ollama-host:11434"
  # ...

alerts:
  # 配置告警通知渠道
  dingtalk:
    enabled: true
    webhook: "your-webhook-url"
  # ...
```

### 4. 运行项目

使用提供的启动脚本运行项目：

```bash
sh run.sh
```

或者直接使用 uvicorn 启动：

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动后，访问浏览器 `http://127.0.0.1:8000` 即可使用。

## 项目结构

```
.
├── app/                 # Python 后端源码
│   ├── main.py          # FastAPI 应用入口
│   ├── llm.py           # LLM 交互逻辑
│   ├── milvus_client.py # Milvus 数据库操作
│   ├── prometheus_adapter.py # Prometheus 数据适配
│   ├── alerts.py        # 告警模块
│   └── config.py        # 配置加载
├── web/                 # 前端资源
│   ├── index.html
│   └── static/
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖
└── run.sh               # 启动脚本
```
