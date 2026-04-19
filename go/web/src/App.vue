<template>
  <div class="container">
    <div class="header">
      <h1>🌐 Nginx 访问统计</h1>
      <p>访客 IP 属地查询</p>
    </div>

    <div class="card">
      <div class="toolbar">
        <div class="toolbar-left">
          <a :class="{ active: sort === 'ip' }" href="/?sort=ip">IP</a>
          <a :class="{ active: sort === 'count' }" href="/?sort=count">次数</a>
        </div>
        <div class="status-badge" :class="running ? 'loading' : 'done'">
          <span class="status-dot"></span>
          <span id="status">{{ running ? `第 ${done} / ${total} 个IP查询中...` : '已加载完成' }}</span>
        </div>
      </div>

      <div v-if="data.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>访客 IP</th>
              <th>访问次数</th>
              <th>属地</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in data" :key="item.ip">
              <td class="ip-cell"><code>{{ item.ip }}</code></td>
              <td class="count-cell">{{ item.count }}</td>
              <td>
                <div v-if="item.status === 'pending'" class="location-loading">
                  <span class="spinner"></span>
                  <span>查询中...</span>
                </div>
                <span v-else class="location-main">{{ item.location }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="empty-state">
        <p>暂无访问记录</p>
      </div>
    </div>

    <div class="footer">
      缓存有效期 30 天 · SQLite 本地存储
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const data = ref([])
const sort = ref('count')
const total = ref(0)
const done = ref(0)
const running = ref(false)

async function fetchData() {
  const res = await fetch(`/api/data?sort=${sort.value}`)
  data.value = await res.json()
  
  const st = await fetch('/api/status').then(r => r.json())
  total.value = st.total
  done.value = st.done
  running.value = st.running
}

async function updateStatus() {
  const st = await fetch('/api/status').then(r => r.json())
  total.value = st.total
  done.value = st.done
  running.value = st.running
  
  if (st.running) {
    setTimeout(() => location.reload(), 2000)
  } else if (st.done > 0 && st.done === st.total) {
    setTimeout(() => location.reload(), 1500)
  }
}

onMounted(() => {
  fetchData()
  setInterval(updateStatus, 3000)
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: linear-gradient(135deg, #009900 0%, #00b804 100%);
  min-height: 100vh;
  padding: 40px 20px;
}
.container { max-width: 1200px; margin: 0 auto; }

.header { text-align: center; margin-bottom: 30px; }
.header h1 {
  color: white;
  font-size: 2.5rem;
  font-weight: 700;
  text-shadow: 0 2px 10px rgba(0,0,0,0.2);
}
.header p { color: rgba(255,255,255,0.8); margin-top: 8px; }

.card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  overflow: hidden;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  flex-wrap: wrap;
  gap: 16px;
}

.toolbar a {
  padding: 8px 16px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 500;
  font-size: 14px;
  transition: all 0.2s;
}
.toolbar a.active { background: #009900; color: white; }
.toolbar a:not(.active) { background: white; color: #009900; border: 1px solid #009900; }

.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}
.status-badge.loading { background: #fef3c7; color: #d97706; }
.status-badge.done { background: #d1fae5; color: #059669; }

.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  animation: pulse 1.5s infinite;
}
.loading .status-dot { background: #d97706; }
.done .status-dot { background: #059669; animation: none; }
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}

.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th {
  padding: 16px 24px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  background: #f8fafc;
}
td { padding: 16px 24px; border-bottom: 1px solid #f1f5f9; }
tr:hover { background: #f8fafc; }

.ip-cell code {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 14px;
  color: #1e293b;
  background: #f1f5f9;
  padding: 4px 10px;
  border-radius: 6px;
}
.count-cell { font-size: 18px; font-weight: 700; color: #009900; }

.location-loading {
  color: #d97706;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}
.location-main { color: #059669; font-weight: 600; }

.spinner {
  width: 14px; height: 14px;
  border: 2px solid #fcd34d;
  border-top-color: #d97706;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.empty-state { text-align: center; padding: 60px 20px; color: #94a3b8; }
.footer { text-align: center; padding: 20px; color: rgba(255,255,255,0.6); font-size: 13px; }
</style>