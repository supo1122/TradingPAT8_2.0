import os
import sys
import json
import base64
import csv
import time
import webview
from datetime import datetime

# API 類別
class Api:
    def __init__(self, app_path):
        self.app_path = app_path
        self.data_file = os.path.join(app_path, "trades.json")
        self.config_file = os.path.join(app_path, "config.json")
        self.img_folder = os.path.join(app_path, "images")
        if not os.path.exists(self.img_folder):
            os.makedirs(self.img_folder)

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                return "[]"
        return "[]"

    def save_data(self, data_json):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                f.write(data_json)
            return "ok"
        except Exception as e:
            return str(e)

    def load_methods(self):
        default = ["三推底", "三推頂", "雙底", "雙頂", "突破有跟隨", "突破無跟隨", "TR", "重大趨勢反轉"]
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                return json.dumps(default)
        return json.dumps(default)

    def save_methods(self, json_str):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(json_str)
        return "ok"

    def save_image(self, base64_str):
        try:
            if "," in base64_str:
                header, encoded = base64_str.split(",", 1)
            else:
                encoded = base64_str
            
            data = base64.b64decode(encoded)
            filename = f"img_{int(time.time()*1000)}.jpg"
            filepath = os.path.join(self.img_folder, filename)
            
            with open(filepath, "wb") as f:
                f.write(data)
            return filename
        except Exception as e:
            return f"error: {str(e)}"

    # 新增：直接讀取圖片並轉回 Base64 給前端顯示 (解決路徑問題)
    def get_image_base64(self, filename):
        try:
            filepath = os.path.join(self.img_folder, filename)
            if not os.path.exists(filepath):
                return ""
            with open(filepath, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/jpeg;base64,{encoded}"
        except:
            return ""

    def export_csv(self, json_str):
        try:
            data = json.loads(json_str)
            if not data: return "no data"
            
            csv_file = os.path.join(self.app_path, f"export_{int(time.time())}.csv")
            
            # 扁平化處理以便 CSV 寫入
            flat_data = []
            for item in data:
                flat_item = item.copy()
                # 移除圖片欄位避免 CSV 太大或亂碼，只留檔名
                if 'img' not in flat_item: flat_item['img'] = ""
                flat_data.append(flat_item)

            if not flat_data: return "empty"
            keys = flat_data[0].keys()
            
            with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(flat_data)
            
            return f"已匯出至: {csv_file}"
        except Exception as e:
            return str(e)

# 前端介面
HTML_CODE = r"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Journal V6.1</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --primary: #2c3e50; --bg: #f8f9fa; --card-bg: #fff; --border: #e9ecef; --text: #495057; --win: #27ae60; --loss: #c0392b; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 30px; }
        .container { max-width: 1400px; margin: 0 auto; }

        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }
        h1 { font-weight: 300; letter-spacing: 1px; color: var(--primary); font-size: 26px; }
        .btn-group { display: flex; gap: 10px; }
        button { cursor: pointer; border: none; border-radius: 4px; padding: 8px 16px; font-size: 13px; transition: 0.2s; }
        .btn-save { background: var(--primary); color: white; }
        .btn-clear { background: #fff; border: 1px solid #ffcdd2; color: #e57373; }
        .btn-export { background: #2ecc71; color: white; }

        .settings-bar { background: #e3f2fd; padding: 10px 20px; border-radius: 6px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; color: #1565c0; font-size: 13px; }
        .settings-bar input { width: 80px; padding: 5px; border: 1px solid #90caf9; border-radius: 4px; color: #1565c0; font-weight: bold; text-align: center; }

        .stats-bar { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: var(--card-bg); padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); text-align: center; }
        .stat-val { font-size: 28px; font-weight: 600; color: var(--primary); margin-bottom: 5px; }

        .main-grid { display: grid; grid-template-columns: 320px 1fr; gap: 25px; align-items: start; }
        
        /* 修正：移除 sticky，讓輸入區自然流動，解決滑動問題 */
        .input-section { background: var(--card-bg); padding: 25px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); }
        
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 12px; color: #999; margin-bottom: 6px; font-weight: 600; }
        input, select { width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 4px; font-size: 13px; background: #fff; outline: none; }
        
        .img-drop-zone { border: 2px dashed #ddd; padding: 20px; text-align: center; color: #999; font-size: 12px; border-radius: 4px; cursor: pointer; transition: 0.2s; }
        .img-drop-zone:hover { border-color: var(--primary); color: var(--primary); background: #f8f9fa; }
        .img-preview { max-width: 100%; margin-top: 10px; border-radius: 4px; display: none; }

        .btn-add { width: 100%; background: var(--primary); color: white; padding: 12px; font-weight: 600; margin-top: 10px; font-size: 14px; }
        .btn-add:hover { background: #34495e; }

        .charts-row { display: grid; grid-template-columns: 1.5fr 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .chart-box { background: var(--card-bg); padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); height: 350px; position: relative; display: flex; flex-direction: column; }
        .chart-container { flex: 1; position: relative; min-height: 0; }

        .heatmap-container { overflow-x: auto; margin-top: 20px; }
        .heatmap-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .heatmap-table th, .heatmap-table td { border: 1px solid #eee; padding: 8px; text-align: center; }
        .heatmap-table th { background: #f8f9fa; color: #666; }
        .heatmap-table td { color: #333; }

        .table-box { background: var(--card-bg); border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.03); }
        .data-table { width: 100%; border-collapse: collapse; }
        .data-table th { text-align: left; padding: 12px 20px; border-bottom: 1px solid var(--border); font-size: 11px; color: #999; text-transform: uppercase; }
        .data-table td { padding: 12px 20px; border-bottom: 1px solid #f9f9f9; font-size: 13px; vertical-align: middle; }
        
        .win-text { color: var(--win); font-weight: 600; }
        .loss-text { color: var(--loss); font-weight: 600; }
        .tag { padding: 2px 6px; border-radius: 4px; background: #eee; font-size: 11px; color: #666; margin-right: 4px; white-space: nowrap; }
        
        .img-icon { cursor: pointer; font-size: 16px; color: #3498db; }
        .img-popup { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1000; background: white; padding: 10px; border-radius: 8px; box-shadow: 0 5px 20px rgba(0,0,0,0.3); display: none; max-height: 80vh; max-width: 80vw; }
        .img-popup img { max-width: 100%; max-height: 75vh; border-radius: 4px; }
        .overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 999; display: none; }
    </style>
</head>
<body>

<div class="overlay" onclick="closeImg()"></div>
<div class="img-popup" id="popup"><img id="popupImg" src=""></div>

<div class="container">
    <header>
        <h1>TRADING JOURNAL <span style="font-size:14px; color:#ccc; margin-left:10px;">V6.1 Fixed</span></h1>
        <div class="btn-group">
            <button class="btn-export" onclick="exportCSV()">📂 匯出 Excel</button>
            <button class="btn-save" onclick="saveData()">💾 備份</button>
            <button class="btn-clear" onclick="clearAllData()">🗑️ 清空</button>
        </div>
    </header>

    <div class="settings-bar">
        <span>💰 設定 1R 金額 (USD): $</span>
        <input type="number" id="oneRValue" value="200" onchange="renderUI()">
    </div>

    <div class="stats-bar">
        <div class="stat-card">
            <div class="stat-val" id="totalProfit">$0</div>
            <div class="stat-label">總獲利</div>
        </div>
        <div class="stat-card">
            <div class="stat-val" id="totalR">0R</div>
            <div class="stat-label">累積 R</div>
        </div>
        <div class="stat-card">
            <div class="stat-val" id="winRate">0%</div>
            <div class="stat-label">勝率</div>
        </div>
        <div class="stat-card">
            <div class="stat-val" id="pf">0.0</div>
            <div class="stat-label">PF</div>
        </div>
    </div>

    <div class="main-grid">
        <div class="input-section">
            <div class="form-group">
                <label>日期時間 (Time)</label>
                <input type="datetime-local" id="tradeTime">
            </div>

            <div class="form-group">
                <label>截圖 (Ctrl+V 或 點擊上傳)</label>
                <div class="img-drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
                    📷 點擊選擇圖片 或 直接貼上
                </div>
                <input type="file" id="fileInput" accept="image/*" style="display:none" onchange="handleFile(this.files[0])">
                <img id="preview" class="img-preview">
            </div>

            <div class="form-group">
                <label>市場背景</label>
                <select id="context">
                    <option value="強趨勢 (Strong Trend)">強趨勢</option>
                    <option value="交易區間 (Trading Range)">交易區間</option>
                    <option value="寬通道 (Broad Channel)">寬通道</option>
                    <option value="窄通道 (Tight Channel)">窄通道</option>
                    <option value="突破模式 (Breakout Mode)">突破模式</option>
                    <option value="高潮 (Climax)">高潮</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>策略</label>
                <select id="method"></select>
                <div style="margin-top:5px; display:flex; gap:5px;">
                    <button style="flex:1; background:#eee;" onclick="addMethod()">+ 新增</button>
                    <button style="flex:1; background:#eee;" onclick="delMethod()">- 刪除</button>
                </div>
            </div>

            <div class="form-group"><label>型態</label><select id="type"><option value="Swing">Swing</option><option value="Scalp">Scalp</option></select></div>
            <div class="form-group"><label>情緒</label><select id="emotion"><option value="平靜">平靜</option><option value="急躁">急躁</option><option value="猶豫">猶豫</option><option value="報復">報復</option></select></div>
            
            <div class="form-group">
                <label>結果</label>
                <select id="result" onchange="updateR()">
                    <option value="獲利">✅ 獲利</option>
                    <option value="虧損">❌ 虧損</option>
                    <option value="打平">⚪ 打平</option>
                </select>
            </div>
            <div class="form-group"><label>R 值</label><input type="number" id="rValue" step="0.1" value="2.0"></div>
            <div class="form-group"><label>備註</label><input type="text" id="remark"></div>

            <button class="btn-add" onclick="addTrade()">新增交易</button>
        </div>

        <div class="content-section">
            <div class="charts-row">
                <div class="chart-box">
                    <div style="font-weight:600; margin-bottom:10px;">資金曲線 ($)</div>
                    <div class="chart-container"><canvas id="equityChart"></canvas></div>
                </div>
                <div class="chart-box">
                    <div style="font-weight:600; margin-bottom:10px;">時段損益 (Hourly PnL)</div>
                    <div class="chart-container"><canvas id="hourChart"></canvas></div>
                </div>
                <div class="chart-box">
                    <div style="font-weight:600; margin-bottom:10px;">背景損益 (Context)</div>
                    <div class="chart-container"><canvas id="contextChart"></canvas></div>
                </div>
            </div>

            <div class="chart-box" style="margin-bottom:30px; height:auto; min-height:180px;">
                <div style="font-weight:600; margin-bottom:10px;">🔥 策略勝率矩陣</div>
                <div class="heatmap-container" id="heatmapContainer"></div>
            </div>

            <div class="table-box">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>時間</th>
                            <th>圖</th>
                            <th>背景/策略</th>
                            <th>結果</th>
                            <th>R/$</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
    let trades = [];
    let methods = [];
    let currentImgBase64 = null;
    let chartInstances = {};

    window.addEventListener('pywebviewready', () => {
        loadData();
        loadMethods();
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        document.getElementById('tradeTime').value = now.toISOString().slice(0,16);
    });

    document.addEventListener('paste', e => {
        const items = e.clipboardData.items;
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                const blob = items[i].getAsFile();
                handleFile(blob);
            }
        }
    });

    function handleFile(file) {
        if(!file) return;
        const reader = new FileReader();
        reader.onload = e => {
            currentImgBase64 = e.target.result;
            const img = document.getElementById('preview');
            img.src = currentImgBase64;
            img.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }

    function loadData() {
        pywebview.api.load_data().then(res => {
            trades = JSON.parse(res);
            trades.forEach(t => {
                if(!t.time) t.time = new Date().toISOString();
            });
            renderUI();
        });
    }

    function loadMethods() {
        pywebview.api.load_methods().then(res => {
            methods = JSON.parse(res);
            renderMethodSelect();
            renderHeatmap();
        });
    }

    function exportCSV() {
        pywebview.api.export_csv(JSON.stringify(trades)).then(alert);
    }

    function renderMethodSelect() {
        const sel = document.getElementById('method');
        const current = sel.value;
        sel.innerHTML = '';
        methods.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            sel.appendChild(opt);
        });
        if(methods.includes(current)) sel.value = current;
    }

    function addMethod() {
        const m = prompt("新策略名稱:");
        if (m && !methods.includes(m)) {
            methods.push(m);
            pywebview.api.save_methods(JSON.stringify(methods));
            renderMethodSelect();
            renderHeatmap();
        }
    }
    
    function delMethod() {
        const m = document.getElementById('method').value;
        if(confirm(`刪除 ${m}?`)) {
            methods = methods.filter(i => i!==m);
            pywebview.api.save_methods(JSON.stringify(methods));
            renderMethodSelect();
            renderHeatmap();
        }
    }

    function updateR() {
        const res = document.getElementById('result').value;
        const rInput = document.getElementById('rValue');
        if (res === '虧損') rInput.value = -1.0;
        else if (res === '打平') rInput.value = 0.0;
        else if (parseFloat(rInput.value) <= 0) rInput.value = 2.0;
    }

    function addTrade() {
        const res = document.getElementById('result').value;
        let r = parseFloat(document.getElementById('rValue').value);
        if (res === '虧損' && r > 0) r = -r;
        if (res === '虧損' && r === 0) r = -1.0;
        if (res === '打平') r = 0.0;

        // 儲存邏輯
        const processTrade = (savedImgName) => {
            const trade = {
                id: Date.now(),
                time: document.getElementById('tradeTime').value,
                img: savedImgName || "",
                context: document.getElementById('context').value,
                method: document.getElementById('method').value,
                trade_type: document.getElementById('type').value,
                emotion: document.getElementById('emotion').value,
                result: res,
                rValue: r,
                remark: document.getElementById('remark').value
            };
            trades.push(trade);
            pywebview.api.save_data(JSON.stringify(trades));
            
            renderUI();
            currentImgBase64 = null;
            document.getElementById('preview').style.display = 'none';
            document.getElementById('preview').src = "";
            document.getElementById('remark').value = "";
        };

        if(currentImgBase64) {
            pywebview.api.save_image(currentImgBase64).then(savedName => {
                processTrade(savedName);
            });
        } else {
            processTrade("");
        }
    }

    function delTrade(id) {
        if(confirm('刪除?')) {
            trades = trades.filter(t => t.id !== id);
            pywebview.api.save_data(JSON.stringify(trades));
            renderUI();
        }
    }
    
    function clearAllData() {
        if(confirm('清空?')) { trades=[]; pywebview.api.save_data(JSON.stringify(trades)); renderUI(); }
    }

    // 修正後的圖片顯示：請求後端讀取 Base64
    function showImg(filename) {
        if(!filename) return;
        pywebview.api.get_image_base64(filename).then(base64Data => {
            if(base64Data) {
                document.getElementById('popupImg').src = base64Data;
                document.querySelector('.overlay').style.display = 'block';
                document.getElementById('popup').style.display = 'block';
            } else {
                alert("圖片讀取失敗 (可能已刪除)");
            }
        });
    }
    
    function closeImg() {
        document.querySelector('.overlay').style.display = 'none';
        document.getElementById('popup').style.display = 'none';
        document.getElementById('popupImg').src = "";
    }

    function renderUI() {
        const dollarPerR = parseFloat(document.getElementById('oneRValue').value) || 200;

        const total = trades.length;
        const totalR = trades.reduce((s, t) => s + t.rValue, 0);
        const totalPnL = totalR * dollarPerR;
        const wins = trades.filter(t => t.result === '獲利').length;
        const winRate = total > 0 ? (wins / total * 100).toFixed(0) + '%' : '0%';
        const grossWin = trades.filter(t => t.rValue > 0).reduce((s,t) => s+t.rValue, 0);
        const grossLoss = Math.abs(trades.filter(t => t.rValue < 0).reduce((s,t) => s+t.rValue, 0));
        const pf = grossLoss > 0 ? (grossWin / grossLoss).toFixed(2) : (grossWin > 0 ? '∞' : '0.0');

        document.getElementById('totalProfit').innerText = (totalPnL >= 0 ? '+$' : '-$') + Math.abs(totalPnL).toLocaleString();
        document.getElementById('totalProfit').style.color = totalPnL >= 0 ? '#27ae60' : '#c0392b';
        document.getElementById('totalR').innerText = totalR.toFixed(1) + 'R';
        document.getElementById('winRate').innerText = winRate;
        document.getElementById('pf').innerText = pf;

        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = '';
        [...trades].reverse().forEach(t => {
            const tr = document.createElement('tr');
            const resClass = t.result === '獲利' ? 'win-text' : (t.result === '虧損' ? 'loss-text' : '');
            const money = (t.rValue * dollarPerR).toFixed(0);
            const dateStr = t.time ? t.time.slice(5, 16).replace('T', ' ') : '-';
            const imgIcon = t.img ? `<span class="img-icon" onclick="showImg('${t.img}')">📷</span>` : '-';
            
            tr.innerHTML = `
                <td style="font-size:12px; color:#999">${dateStr}</td>
                <td>${imgIcon}</td>
                <td>
                    <div style="font-weight:600">${t.method}</div>
                    <div style="font-size:11px; color:#999">${t.context.split('(')[0]}</div>
                </td>
                <td class="${resClass}">${t.result}</td>
                <td>
                    <div class="${resClass}">${t.rValue}R</div>
                    <div style="font-size:11px; color:#666">$${money}</div>
                </td>
                <td><button onclick="delTrade(${t.id})" style="background:none; color:#ccc;">✖</button></td>
            `;
            tbody.appendChild(tr);
        });

        updateCharts(dollarPerR);
        renderHeatmap();
    }

    function updateCharts(dollarPerR) {
        let acc = 0;
        const eqData = trades.map(t => acc += t.rValue * dollarPerR);
        renderChart('equityChart', 'line', trades.map((_, i) => i+1), eqData, '#2980b9');

        const hourPnL = new Array(24).fill(0);
        trades.forEach(t => {
            if(t.time) {
                const h = new Date(t.time).getHours();
                hourPnL[h] += t.rValue * dollarPerR;
            }
        });
        const hours = Array.from({length:24}, (_, i) => i + ":00");
        renderChart('hourChart', 'bar', hours, hourPnL, hourPnL.map(v=>v>=0?'#27ae60':'#c0392b'));

        const ctxPnL = {};
        trades.forEach(t => {
            const c = t.context.split('(')[0];
            if(!ctxPnL[c]) ctxPnL[c] = 0;
            ctxPnL[c] += t.rValue * dollarPerR;
        });
        renderChart('contextChart', 'bar', Object.keys(ctxPnL), Object.values(ctxPnL), Object.values(ctxPnL).map(v=>v>=0?'#27ae60':'#c0392b'), 'y');
    }

    function renderChart(id, type, labels, data, colors, indexAxis='x') {
        if(chartInstances[id]) chartInstances[id].destroy();
        chartInstances[id] = new Chart(document.getElementById(id), {
            type: type,
            data: {
                labels: labels,
                datasets: [{ 
                    data: data, 
                    backgroundColor: colors, 
                    borderColor: '#2980b9', 
                    tension: 0.1, 
                    fill: type==='line' 
                }]
            },
            options: {
                responsive: true, 
                maintainAspectRatio: false, 
                indexAxis: indexAxis,
                plugins: { legend: {display:false} },
                scales: { x: {display: indexAxis!=='y'}, y: {display: indexAxis!=='x'} }
            }
        });
    }

    function renderHeatmap() {
        const container = document.getElementById('heatmapContainer');
        const contexts = ["強趨勢 (Strong Trend)", "交易區間 (Trading Range)", "寬通道 (Broad Channel)", "窄通道 (Tight Channel)", "突破模式 (Breakout Mode)", "高潮 (Climax)"];
        const matrix = {};
        contexts.forEach(c => {
            matrix[c] = {};
            methods.forEach(m => matrix[c][m] = { wins: 0, total: 0 });
        });

        trades.forEach(t => {
            const matchedCtx = contexts.find(c => c === t.context) || t.context;
            if(matrix[matchedCtx] && matrix[matchedCtx][t.method]) {
                matrix[matchedCtx][t.method].total++;
                if(t.result === '獲利') matrix[matchedCtx][t.method].wins++;
            }
        });

        let html = '<table class="heatmap-table"><tr class="heatmap-header-row"><th>背景 \\ 策略</th>';
        methods.forEach(m => html += `<th>${m}</th>`);
        html += '</tr>';

        contexts.forEach(ctx => {
            const shortCtx = ctx.split('(')[0];
            html += `<tr><th>${shortCtx}</th>`;
            methods.forEach(m => {
                const data = matrix[ctx] && matrix[ctx][m] ? matrix[ctx][m] : {wins:0, total:0};
                let bg = '#fff';
                let text = '-';
                if (data.total > 0) {
                    const rate = (data.wins / data.total * 100).toFixed(0);
                    text = `${rate}% <span style="font-size:10px; opacity:0.6">(${data.total})</span>`;
                    if (rate >= 60) bg = '#d4edda';
                    else if (rate >= 40) bg = '#fff3cd';
                    else bg = '#f8d7da';
                }
                html += `<td style="background:${bg}">${text}</td>`;
            });
            html += '</tr>';
        });
        html += '</table>';
        container.innerHTML = html;
    }
</script>
</body>
</html>
"""

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        app_path = os.path.dirname(sys.executable)
    else:
        app_path = os.path.dirname(os.path.abspath(__file__))

    api = Api(app_path)
    webview.create_window('Trading Journal V6.1', html=HTML_CODE, width=1400, height=900, js_api=api)
    webview.start()
