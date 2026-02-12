const q = document.getElementById('query');
const s = document.getElementById('step') || { value: '60s' }; // Step might be removed from UI but kept in logic
const r = document.getElementById('result');
const t = document.getElementById('thought');
const instanceSelect = document.getElementById('instance-select');
const metricSelect = document.getElementById('metric-select');
let chartInstance = null;

// Initialize
async function init() {
  try {
    const res = await fetch('/targets');
    const data = await res.json();
    
    // Populate Instances
    instanceSelect.innerHTML = '';
    if (data.targets && data.targets.length > 0) {
      data.targets.forEach(tgt => {
        const opt = document.createElement('option');
        opt.value = tgt.instance;
        opt.textContent = `${tgt.instance} (${tgt.job}) - ${tgt.health}`;
        instanceSelect.appendChild(opt);
      });
    } else {
      const opt = document.createElement('option');
      opt.textContent = 'No targets found';
      instanceSelect.appendChild(opt);
    }

    // Populate Metrics
    metricSelect.innerHTML = '';
    if (data.metrics && data.metrics.length > 0) {
      data.metrics.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m;
        metricSelect.appendChild(opt);
      });
    }
    
    // Trigger initial query update
    updateQuery();
  } catch (e) {
    console.error(e);
    instanceSelect.innerHTML = '<option>Error loading targets</option>';
  }
}

async function updateMetrics(instance) {
    if (!instance) return;
    metricSelect.innerHTML = '<option>Loading...</option>';
    try {
        const res = await fetch(`/targets?instance=${encodeURIComponent(instance)}`);
        const data = await res.json();
        metricSelect.innerHTML = '';
        if (data.metrics && data.metrics.length > 0) {
            data.metrics.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                metricSelect.appendChild(opt);
            });
            // Select 'up' if available by default
            if (data.metrics.includes('up')) {
                metricSelect.value = 'up';
            }
        } else {
             metricSelect.innerHTML = '<option>No metrics found</option>';
        }
        updateQuery();
    } catch (e) {
        console.error(e);
        metricSelect.innerHTML = '<option>Error loading metrics</option>';
    }
}

function updateQuery() {
  const instance = instanceSelect.value;
  const metric = metricSelect.value;
  if (instance && metric) {
    // Construct PromQL: metric{instance="host:port"}
    q.value = `${metric}{instance="${instance}"}`;
  } else if (metric) {
    q.value = metric;
  }
}

instanceSelect.onchange = () => {
    updateMetrics(instanceSelect.value);
};
metricSelect.onchange = updateQuery;

function renderChart(recentPoints, prediction) {
  const ctx = document.getElementById('chartCanvas').getContext('2d');
  
  // Format data
  // recentPoints is [[ts, val], ...]
  // Use Chinese friendly time format HH:mm:ss
  const formatTime = (ts) => new Date(ts * 1000).toLocaleTimeString('zh-CN', { hour12: false });
  
  const labels = recentPoints.map(p => formatTime(p[0]));
  const dataPoints = recentPoints.map(p => p[1]);
  
  const datasets = [{
    label: '历史数据',
    data: dataPoints,
    borderColor: 'rgb(75, 192, 192)',
    tension: 0.1
  }];

  // If we have prediction points, add them
  if (prediction && Array.isArray(prediction) && prediction.length > 0) {
      // Align prediction points. 
      // We might need to extend labels if prediction points are in future.
      const predData = new Array(dataPoints.length).fill(null);
      // Connect last real point to first pred point
      predData[predData.length - 1] = dataPoints[dataPoints.length - 1];
      
      prediction.forEach(p => {
          labels.push(formatTime(p[0]));
          predData.push(p[1]);
      });
      
      datasets.push({
          label: '预测趋势',
          data: predData,
          borderColor: 'rgb(255, 99, 132)',
          borderDash: [5, 5],
          tension: 0.1
      });
  }
  
  if (chartInstance) {
    chartInstance.destroy();
  }
  
  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          labels: {
            font: {
               family: "'Microsoft YaHei', 'SimHei', sans-serif"
            }
          }
        },
        tooltip: {
            mode: 'index',
            intersect: false,
        }
      },
      scales: {
        x: { 
            display: true,
            ticks: {
                maxRotation: 45,
                minRotation: 45
            }
        },
        y: { beginAtZero: false }
      }
    }
  });
}

document.getElementById('ingest').onclick = async () => {
  r.textContent = '导入中...';
  t.textContent = '';
  const res = await fetch(`/ingest?metric=${encodeURIComponent(q.value)}&step=${encodeURIComponent(s.value)}`, { method: 'POST' });
  const data = await res.json();
  r.textContent = JSON.stringify(data, null, 2);
};

document.getElementById('analyze').onclick = async () => {
  r.textContent = '分析中...';
  t.textContent = '思考中...';
  const res = await fetch(`/analyze?metric=${encodeURIComponent(q.value)}&step=${encodeURIComponent(s.value)}`);
  const data = await res.json();
  
  // Extract thought if present
  if (data.thought) {
    t.textContent = data.thought;
  } else {
    t.textContent = '无思考过程';
  }
  
  renderReport(data);
  
  // Render Chart if data available
  if (data.recent_points) {
    // Check if LLM returned prediction_points
    const predictionPoints = data.prediction_points || [];
    renderChart(data.recent_points, predictionPoints);
  }
};

function renderReport(data) {
    if (data.error) {
        r.innerHTML = `<div class="error" style="color:red">${data.error}</div>`;
        return;
    }
    
    // Fallback if not structured analysis result
    if (!data.title && !data.analysis) {
        r.textContent = JSON.stringify(data, null, 2);
        return;
    }

    const levelColor = getLevelColor(data.level);

    const html = `
        <div class="report-container">
            <div class="report-header" style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #eee; padding-bottom:10px; margin-bottom:10px;">
                <h3 style="margin:0">${data.title || '分析报告'}</h3>
                <span style="background:${levelColor}; color:white; padding:4px 8px; border-radius:4px; font-size:0.9em;">${data.level || '未知'}</span>
            </div>
            
            <div style="margin-bottom:10px;">
                <strong>当前状态:</strong> <span>${data.current_status || '-'}</span>
            </div>
            
            <div style="margin-bottom:10px;">
                <strong>预测结论:</strong> <span>${data.prediction || '-'}</span>
            </div>
            
            <div style="margin-bottom:10px;">
                <strong>核心分析:</strong>
                <p style="margin:5px 0; line-height:1.5; color:#444;">${data.analysis || '-'}</p>
            </div>
            
            <div>
                <strong>建议操作:</strong>
                <div style="margin-top:5px; background:#f9f9f9; padding:10px; border-radius:4px; white-space: pre-line;">${data.action || '-'}</div>
            </div>
        </div>
    `;
    r.innerHTML = html;
}

function getLevelColor(level) {
    if (!level) return '#999';
    if (level.includes('高') || level.includes('High') || level.includes('Critical')) return '#dc3545'; // Red
    if (level.includes('中') || level.includes('Medium') || level.includes('Warn')) return '#ffc107'; // Yellow/Orange
    if (level.includes('正常') || level.includes('Normal') || level.includes('Low')) return '#28a745'; // Green
    return '#17a2b8'; // Blue
}

document.getElementById('alert').onclick = async () => {
  r.textContent = '推送中...';
  try {
    const res = await fetch(`/alert?metric=${encodeURIComponent(q.value)}`, { method: 'POST' });
    const data = await res.json();
    
    if (data.analysis) {
        renderReport(data.analysis);
        // Append alert status
        const statusHtml = `
          <div style="margin-top:15px; border-top:1px dashed #ccc; padding-top:10px;">
              <strong>推送结果:</strong>
              <ul style="margin:5px 0; padding-left:20px;">
                  <li>企业微信: ${data.alerts_sent && data.alerts_sent.wecom ? '✅' : '❌'}</li>
                  <li>钉钉: ${data.alerts_sent && data.alerts_sent.dingtalk ? '✅' : '❌'}</li>
                  <li>邮件: ${data.alerts_sent && data.alerts_sent.email ? '✅' : '❌'}</li>
              </ul>
          </div>
        `;
        r.innerHTML += statusHtml;
    } else {
        r.textContent = JSON.stringify(data, null, 2);
    }
  } catch (e) {
    r.textContent = 'Alert Error: ' + e;
  }
};

init();
