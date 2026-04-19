package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

const (
	LogFile   = "/var/log/nginx/access.log"
	DBFile   = "data/data.db"
	CacheTTL = 30 * 24 * time.Hour
)

type IPItem struct {
	IP       string `json:"ip"`
	Count    int    `json:"count"`
	Location string `json:"location,omitempty"`
	Status  string `json:"status,omitempty"`
}

type QueryStatus struct {
	Total  int `json:"total"`
	Done   int `json:"done"`
	Running bool `json:"running"`
}

var (
	db         *sql.DB
	queryStatus QueryStatus
	queryMu    sync.Mutex
	statusMu   sync.Mutex
)

func initDB() {
	os.MkdirAll("data", 0755)
	var err error
	db, err = sql.Open("sqlite3", DBFile)
	if err != nil {
		log.Fatal(err)
	}
	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS ip_cache (
			ip TEXT PRIMARY KEY,
			location TEXT,
			timestamp INTEGER
		)
	`)
	if err != nil {
		log.Fatal(err)
	}
}

func getCachedLocation(ip string) (string, int64) {
	var location string
	var timestamp int64
	err := db.QueryRow("SELECT location, timestamp FROM ip_cache WHERE ip = ?", ip).Scan(&location, &timestamp)
	if err != nil {
		return "", 0
	}
	if time.Now().Unix()-timestamp < int64(CacheTTL.Seconds()) {
		return location, timestamp
	}
	return "", 0
}

func saveLocation(ip, location string) {
	_, err := db.Exec(
		"INSERT OR REPLACE INTO ip_cache (ip, location, timestamp) VALUES (?, ?, ?)",
		ip, location, time.Now().Unix(),
	)
	if err != nil {
		log.Printf("Save error: %v", err)
	}
}

func fetchFromAPI(ip string) string {
	url := fmt.Sprintf("http://ip-api.com/json/%s?lang=zh-CN", ip)
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "Mozilla/5.0")
	
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("Fetch error: %v", err)
		return ""
	}
	defer resp.Body.Close()
	
	var data map]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return ""
	}
	if status, ok := data["status"].(string); ok && status == "success" {
		country := getString(data, "country")
		region := getString(data, "regionName")
		city := getString(data, "city")
		isp := getString(data, "isp")
		return fmt.Sprintf("%s %s %s [%s]", country, region, city, isp)
	}
	return ""
}

func getString(m map]interface{}, key string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	return ""
}

func queryIP(ip string) string {
	if loc, _ := getCachedLocation(ip); loc != "" {
		return loc
	}
	location := fetchFromAPI(ip)
	if location != "" {
		saveLocation(ip, location)
	}
	return location
}

func queryIPsBackground(ips []string) {
	statusMu.Lock()
	queryStatus = QueryStatus{Total: len(ips), Done: 0, Running: true}
	statusMu.Unlock()
	
	for _, ip := range ips {
		queryIP(ip)
		statusMu.Lock()
		queryStatus.Done++
		statusMu.Unlock()
	}
	
	statusMu.Lock()
	queryStatus.Running = false
	statusMu.Unlock()
}

func getLogData() []IPItem {
	if _, err := os.Stat(LogFile); os.IsNotExist(err) {
		return []IPItem{}
	}
	
	content, err := os.ReadFile(LogFile)
	if err != nil {
		log.Printf("Log read error: %v", err)
		return []IPItem{}
	}
	
	ipCounts := make(map[string]int)
	lines := strings.Split(string(content), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		parts := strings.Fields(line)
		if len(parts) > 0 {
			ipCounts[parts[0]]++
		}
	}
	
	items := make([]IPItem, 0, len(ipCounts))
	for ip, count := range ipCounts {
		items = append(items, IPItem{IP: ip, Count: count})
	}
	return items
}

// HomePage 主页模板
var HomePage = template.Must(template.New("index").Parse(`<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nginx 访问统计</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: white;
            font-size: 2.5rem;
            font-weight: 700;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .header p {
            color: rgba(255,255,255,0.8);
            margin-top: 8px;
        }
        
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
        
        .toolbar a.active {
            background: #667eea;
            color: white;
        }
        
        .toolbar a:not(.active) {
            background: white;
            color: #64748b;
            border: 1px solid #e2e8f0;
        }
        
        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }
        
        .status-badge.loading {
            background: #fef3c7;
            color: #d97706;
        }
        
        .status-badge.done {
            background: #d1fae5;
            color: #059669;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        
        .loading .status-dot { background: #d97706; }
        .done .status-dot { background: #059669; animation: none; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }
        
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
        
        td {
            padding: 16px 24px;
            border-bottom: 1px solid #f1f5f9;
        }
        
        tr:last-child td { border-bottom: none; }
        tr:hover { background: #f8fafc; }
        
        .ip-cell code {
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            color: #1e293b;
            background: #f1f5f9;
            padding: 4px 10px;
            border-radius: 6px;
        }
        
        .count-cell {
            font-size: 18px;
            font-weight: 700;
            color: #667eea;
        }
        
        .location-loading {
            color: #d97706;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .location-main {
            color: #059669;
            font-weight: 600;
        }
        
        .spinner {
            width: 14px;
            height: 14px;
            border: 2px solid #fcd34d;
            border-top-color: #d97706;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #94a3b8;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: rgba(255,255,255,0.6);
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 Nginx 访问统计</h1>
            <p>访客 IP 属地查询</p>
        </div>
        
        <div class="card">
            <div class="toolbar">
                <div>
                    <a class="{{ if .CurrentSort }}active{{ else }}{{ end }}" href="/?sort=ip">IP</a>
                    <a class="{{ if eq .CurrentSort }}active{{ else }}{{ end }}" href="/?sort=count">次数</a>
                </div>
                <div class="status-badge {{ if .Running }}loading{{ else }}done{{ end }}">
                    <span class="status-dot"></span>
                    <span id="status">{{ if .Running }}第 {{ .Done }} / {{ .Total }} 个IP查询中...{{ else }}已加载完成{{ end }}</span>
                </div>
            </div>
            
            {{ if .Data }}
            <table>
                <thead>
                    <tr>
                        <th>访客 IP</th>
                        <th>访问次数</th>
                        <th>属地</th>
                    </tr>
                </thead>
                <tbody>
                    {{ range .Data }}
                    <tr>
                        <td class="ip-cell"><code>{{ .IP }}</code></td>
                        <td class="count-cell">{{ .Count }}</td>
                        <td>
                            {{ if eq .Status "pending" }}
                            <div class="location-loading">
                                <span class="spinner"></span>
                                <span>查询中...</span>
                            </div>
                            {{ else }}
                            <span class="location-main">{{ .Location }}</span>
                            {{ end }}
                        </td>
                    </tr>
                    {{ end }}
                </tbody>
            </table>
            {{ else }}
            <div class="empty-state">
                <p>暂无访问记录</p>
            </div>
            {{ end }}
        </div>
        
        <div class="footer">
            缓存有效期 30 天 · SQLite 本地存储
        </div>
    </div>

    <script>
        async function updateStatus() {
            try {
                const res = await fetch('/api/status');
                const st = await res.json();
                
                if (st.running) {
                    document.getElementById('status').innerText = '第 ' + st.done + ' / ' + st.total + ' 个IP查询中...';
                    setTimeout(() => location.reload(), 2000);
                } else if (st.done > 0 && st.done === st.total) {
                    document.getElementById('status').innerText = '已加载完成';
                    setTimeout(() => location.reload(), 1500);
                }
            } catch(e) {}
        }
        
        {{ if .Running }}
        setInterval(updateStatus, 3000);
        {{ end }}
    </script>
</body>
</html>`

func main() {
	initDB()
	
	r := gin.Default()
	
	// 解析模板
	tmpl := template.Must(template.New("index").Parse(HomePage))
	r.SetHTMLTemplate(tmpl)
	
	// 首页
	r.GET("/", func(c *gin.Context) {
		sortBy := c.DefaultQuery("sort", "count")
		items := getLogData()
		
		// 排序
		if sortBy == "ip" {
			sort.Slice(items, func(i, j int) bool {
				return items[i].IP < items[j].IP
			})
		} else {
			sort.Slice(items, func(i, j int) bool {
				return items[i].Count > items[j].Count
			})
		}
		
		// 填充属地
		var pendingIPs []string
		for i := range items {
			if loc, _ := getCachedLocation(items[i].IP); loc != "" {
				items[i].Location = loc
				items[i].Status = "done"
			} else {
				items[i].Location = ""
				items[i].Status = "pending"
				pendingIPs = append(pendingIPs, items[i].IP)
			}
		}
		
		// 启动后台查询
		statusMu.Lock()
		running := queryStatus.Running
		statusMu.Unlock()
		
		if len(pendingIPs) > 0 && !running {
			go queryIPsBackground(pendingIPs)
		}
		
		statusMu.Lock()
		st := QueryStatus{Total: queryStatus.Total, Done: queryStatus.Done, Running: queryStatus.Running}
		statusMu.Unlock()
		
		c.HTML(http.StatusOK, "index", gin.H{
			"Data":        items,
			"CurrentSort": sortBy,
			"Total":       st.Total,
			"Done":        st.Done,
			"Running":     st.Running,
		})
	})
	
	// 状态 API
	r.GET("/api/status", func(c *gin.Context) {
		statusMu.Lock()
		defer statusMu.Unlock()
		c.JSON(http.StatusOK, queryStatus)
	})
	
	// 数据 API (JSON)
	r.GET("/api/data", func(c *gin.Context) {
		sortBy := c.DefaultQuery("sort", "count")
		items := getLogData()
		
		if sortBy == "ip" {
			sort.Slice(items, func(i, j int) bool {
				return items[i].IP < items[j].IP
			})
		} else {
			sort.Slice(items, func(i, j int) bool {
				return items[i].Count > items[j].Count
			})
		}
		
		var pendingIPs []string
		for i := range items {
			if loc, _ := getCachedLocation(items[i].IP); loc != "" {
				items[i].Location = loc
				items[i].Status = "done"
			} else {
				items[i].Status = "pending"
				pendingIPs = append(pendingIPs, items[i].IP)
			}
		}
		
		// 启动后台查询
		statusMu.Lock()
		running := queryStatus.Running
		statusMu.Unlock()
		
		if len(pendingIPs) > 0 && !running {
			go queryIPsBackground(pendingIPs)
		}
		
		c.JSON(http.StatusOK, items)
	})
	
	log.Println("Server started at :60418")
	r.Run(":60418")
}