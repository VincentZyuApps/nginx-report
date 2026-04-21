package main

import (
	"bufio"
	"compress/gzip"
	"database/sql"
	"encoding/json"
	"fmt"
	"html/template"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"golang.org/x/text/encoding/simplifiedchinese"
	"golang.org/x/text/transform"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

// ==================== 配置 ====================

const (
	logDir   = "/var/log/nginx"
	cacheTTL = 30 * 24 * 3600 // 30天
	port     = "60419"
)

var dbPath = func() string {
	if p := os.Getenv("DB_PATH"); p != "" {
		return p
	}
	return "data/data.db"
}()

// ==================== 全局状态 ====================

var db *sql.DB

type QueryStatus struct {
	Total     int     `json:"total"`
	Done      int     `json:"done"`
	Running   bool    `json:"running"`
	API       string  `json:"api"`
	Retry     int     `json:"retry"`
	NextRetry float64 `json:"next_retry"`
}

var (
	qStatus QueryStatus
	qMu     sync.Mutex
)

// ==================== 数据库 ====================

func initDB() {
	os.MkdirAll(filepath.Dir(dbPath), 0755)
	var err error
	db, err = sql.Open("sqlite3", dbPath)
	if err != nil {
		log.Fatal(err)
	}
	db.Exec(`CREATE TABLE IF NOT EXISTS ip_cache (
		ip TEXT PRIMARY KEY, location TEXT, api_source TEXT, timestamp INTEGER)`)
}

func dbGet(ip string) (location, apiSource string, ok bool) {
	var ts int64
	err := db.QueryRow("SELECT location, api_source, timestamp FROM ip_cache WHERE ip=?", ip).
		Scan(&location, &apiSource, &ts)
	if err != nil || time.Now().Unix()-ts > cacheTTL {
		return "", "", false
	}
	return location, apiSource, true
}

func dbSet(ip, location, apiSource string) {
	db.Exec("INSERT OR REPLACE INTO ip_cache VALUES (?,?,?,?)", ip, location, apiSource, time.Now().Unix())
}

// ==================== 日志解析 ====================

type LogFile struct {
	Key      string
	Label    string
	Filename string
	Date     string
}

func getAllLogFiles() []LogFile {
	var files []LogFile
	p := logDir + "/access.log"
	if fi, err := os.Stat(p); err == nil {
		files = append(files, LogFile{"current", "当前", "access.log", fi.ModTime().Format("01-02")})
	}
	for i := 1; i < 20; i++ {
		p := fmt.Sprintf("%s/access.log.%d", logDir, i)
		gz := p + ".gz"
		if fi, err := os.Stat(p); err == nil {
			files = append(files, LogFile{fmt.Sprintf("access.log.%d", i), fmt.Sprintf("%d", i), fmt.Sprintf("access.log.%d", i), fi.ModTime().Format("01-02")})
		} else if fi, err := os.Stat(gz); err == nil {
			files = append(files, LogFile{fmt.Sprintf("access.log.%d.gz", i), fmt.Sprintf("%d", i), fmt.Sprintf("access.log.%d.gz", i), fi.ModTime().Format("01-02")})
		} else if i >= 5 {
			break
		}
	}
	return files
}

func getLogPath(logfile string) string {
	if logfile == "current" {
		return logDir + "/access.log"
	}
	return logDir + "/" + logfile
}

type LogItem struct {
	IP        string
	Count     int
	Location  string
	APISource string
	Status    string // "done" | "pending"
}

func readLogIPs(path string) (map[string]int, error) {
	var r io.Reader
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	if strings.HasSuffix(path, ".gz") {
		gr, err := gzip.NewReader(f)
		if err != nil {
			return nil, err
		}
		defer gr.Close()
		r = gr
	} else {
		r = f
	}

	counts := make(map[string]int)
	sc := bufio.NewScanner(r)
	for sc.Scan() {
		line := sc.Text()
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) > 0 {
			counts[fields[0]]++
		}
	}
	return counts, nil
}

// ==================== IP 查询 API ====================

var countryMap = map[string]string{
	"China": "中国", "United States": "美国", "United Kingdom": "英国",
	"Russia": "俄罗斯", "Germany": "德国", "Japan": "日本",
	"South Korea": "韩国", "Singapore": "新加坡", "Hong Kong": "香港",
	"Taiwan": "台湾", "France": "法国", "India": "印度",
	"Canada": "加拿大", "Australia": "澳大利亚", "Brazil": "巴西",
	"Netherlands": "荷兰", "Ireland": "爱尔兰", "Switzerland": "瑞士",
	"South Africa": "南非",
}

var ispKeywords = []string{"电信", "联通", "移动", "铁通", "教育网", "科技网"}

func simplifyISP(s string) string {
	for _, k := range ispKeywords {
		if strings.Contains(s, k) {
			return k
		}
	}
	if len([]rune(s)) > 15 {
		return string([]rune(s)[:15])
	}
	return s
}

func normLoc(country, region, city, isp string) string {
	var parts []string
	cn := countryMap[country]
	if cn == "" {
		cn = country
	}
	if cn == "中国" {
		if region != "" {
			parts = append(parts, region)
		}
	} else if cn != "" {
		parts = append(parts, cn)
		if region != "" && region != country {
			parts = append(parts, region)
		}
	}
	if city != "" {
		parts = append(parts, city)
	}
	result := strings.Join(parts, " ")
	if isp != "" {
		ispTxt := simplifyISP(isp)
		if ispTxt != "" {
			result += " [" + ispTxt + "]"
		}
	}
	return strings.TrimSpace(result)
}

func httpGet(url string) ([]byte, error) {
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "Mozilla/5.0")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	return io.ReadAll(resp.Body)
}

func fetchCIP(ip string) string {
	body, err := httpGet("http://www.cip.cc/" + ip)
	if err != nil {
		return ""
	}
	text := string(body)
	addrRe := regexp.MustCompile(`地址\s*:\s*(.+)`)
	ispRe := regexp.MustCompile(`运营商\s*:\s*(.+)`)
	am := addrRe.FindStringSubmatch(text)
	if am == nil {
		return ""
	}
	result := strings.TrimSpace(am[1])
	if im := ispRe.FindStringSubmatch(text); im != nil {
		ispTxt := simplifyISP(strings.TrimSpace(im[1]))
		if ispTxt != "" {
			result += " [" + ispTxt + "]"
		}
	}
	return result
}

func fetchBaidu(ip string) string {
	body, err := httpGet("https://opendata.baidu.com/api.php?co=&resource_id=6006&oe=utf8&query=" + ip)
	if err != nil {
		return ""
	}
	var data struct {
		Status string `json:"status"`
		Data   []struct {
			Location string `json:"location"`
		} `json:"data"`
	}
	if json.Unmarshal(body, &data) != nil || data.Status != "0" || len(data.Data) == 0 {
		return ""
	}
	parts := strings.Fields(data.Data[0].Location)
	if len(parts) == 0 {
		return ""
	}
	result := parts[0]
	if len(parts) > 1 {
		ispTxt := simplifyISP(parts[1])
		if ispTxt != "" {
			result += " [" + ispTxt + "]"
		}
	}
	return result
}

func fetchIPSB(ip string) string {
	body, err := httpGet("https://api.ip.sb/geoip/" + ip)
	if err != nil {
		return ""
	}
	var data map[string]interface{}
	if json.Unmarshal(body, &data) != nil {
		return ""
	}
	str := func(k string) string {
		if v, ok := data[k].(string); ok {
			return v
		}
		return ""
	}
	return normLoc(str("country"), str("region"), str("city"), str("isp"))
}

func fetchPconline(ip string) string {
	body, err := httpGet("https://whois.pconline.com.cn/ipJson.jsp?ip=" + ip + "&json=true")
	if err != nil {
		return ""
	}
	utf8, _, err := transform.Bytes(simplifiedchinese.GBK.NewDecoder(), body)
	if err != nil {
		utf8 = body
	}
	var data map[string]interface{}
	if json.Unmarshal(utf8, &data) != nil {
		return ""
	}
	pro, _ := data["pro"].(string)
	city, _ := data["city"].(string)
	if pro == "" {
		return ""
	}
	return strings.TrimSpace(pro + " " + city)
}

func fetchIPWhois(ip string) string {
	body, err := httpGet("https://ipwhois.app/json/" + ip)
	if err != nil {
		return ""
	}
	var data map[string]interface{}
	if json.Unmarshal(body, &data) != nil {
		return ""
	}
	str := func(k string) string {
		if v, ok := data[k].(string); ok {
			return v
		}
		return ""
	}
	return normLoc(str("country"), str("region"), str("city"), str("isp"))
}

func fetchIPAPI(ip string) string {
	body, err := httpGet("http://demo.ip-api.com/json/" + ip + "?fields=66842623&lang=zh-CN")
	if err != nil {
		return ""
	}
	var data map[string]interface{}
	if json.Unmarshal(body, &data) != nil {
		return ""
	}
	if data["status"] != "success" {
		return ""
	}
	str := func(k string) string {
		if v, ok := data[k].(string); ok {
			return v
		}
		return ""
	}
	return normLoc(str("country"), str("regionName"), str("city"), str("isp"))
}

type apiDef struct {
	name      string
	fn        func(string) string
	rateLimit bool
}

var apis = []apiDef{
	{"cip", fetchCIP, false},
	{"baidu", fetchBaidu, false},
	{"ip.sb", fetchIPSB, false},
	{"pconline", fetchPconline, false},
	{"ipwhois", fetchIPWhois, false},
	{"ip-api", fetchIPAPI, true},
}

var apiIndex int

func fetchLocationWithSource(ip string) (location, apiName string) {
	for i := range apis {
		idx := (apiIndex + i) % len(apis)
		a := apis[idx]
		loc := a.fn(ip)
		if loc != "" {
			apiIndex = idx
			if a.rateLimit {
				time.Sleep(1500 * time.Millisecond)
			}
			return loc, a.name
		}
	}
	return "", ""
}

func getCurrentAPI() string {
	return apis[apiIndex].name
}

// ==================== 后台查询 ====================

func queryIPsBackground(ips []string) {
	qMu.Lock()
	qStatus = QueryStatus{Total: len(ips), Running: true, API: getCurrentAPI()}
	qMu.Unlock()

	for idx, ip := range ips {
		delay := time.Second
		attempt := 0
		for {
			log.Printf("[%d/%d] attempt %d %s", idx+1, len(ips), attempt+1, ip)
			loc, apiUsed := fetchLocationWithSource(ip)

			qMu.Lock()
			if apiUsed != "" {
				qStatus.API = apiUsed
			}
			qStatus.Retry = attempt
			if loc == "" {
				qStatus.NextRetry = delay.Seconds()
			} else {
				qStatus.NextRetry = 0
			}
			qMu.Unlock()

			if loc != "" {
				dbSet(ip, loc, apiUsed)
				qMu.Lock()
				qStatus.Done++
				qMu.Unlock()
				break
			}
			attempt++
			time.Sleep(delay)
			if delay < 32*time.Second {
				delay *= 2
			}
		}
		time.Sleep(50 * time.Millisecond)
	}

	qMu.Lock()
	qStatus.Running = false
	qMu.Unlock()
}

// ==================== HTTP 处理 ====================

var tmpl = template.Must(template.New("index").Funcs(template.FuncMap{
	"ne": func(a, b string) bool { return a != b },
	"eq": func(a, b string) bool { return a == b },
}).ParseFiles("index.html"))

type PageData struct {
	Data          []LogItem
	AllLogFiles   []LogFile
	CurrentLogfile string
	CurrentSort   string
	CurrentOrder  string
	UseCustomFont bool
	Running       bool
	QS            QueryStatus
	LogPath       string
	LogMtime      string
}

func indexHandler(c *gin.Context) {
	sortBy := c.DefaultQuery("sort", "")
	order := c.DefaultQuery("order", "")
	font := c.DefaultQuery("font", "")
	logfile := c.DefaultQuery("logfile", "")

	if sortBy == "" || order == "" || font == "" {
		c.Redirect(http.StatusFound, "/?logfile=current&sort=count&order=desc&font=enabled")
		return
	}
	if logfile == "" {
		logfile = "current"
	}

	logPath := getLogPath(logfile)
	counts, _ := readLogIPs(logPath)

	items := make([]LogItem, 0, len(counts))
	for ip, cnt := range counts {
		items = append(items, LogItem{IP: ip, Count: cnt})
	}

	// 排序
	isDesc := order == "desc"
	sort.Slice(items, func(i, j int) bool {
		if sortBy == "ip" {
			if isDesc {
				return items[i].IP > items[j].IP
			}
			return items[i].IP < items[j].IP
		}
		if isDesc {
			return items[i].Count > items[j].Count
		}
		return items[i].Count < items[j].Count
	})

	// 填充缓存
	var pending []string
	for i := range items {
		if loc, api, ok := dbGet(items[i].IP); ok {
			items[i].Location = loc
			items[i].APISource = api
			items[i].Status = "done"
		} else {
			items[i].Status = "pending"
			pending = append(pending, items[i].IP)
		}
	}

	qMu.Lock()
	running := qStatus.Running
	qMu.Unlock()
	if len(pending) > 0 && !running {
		go queryIPsBackground(pending)
	}

	// 日志文件时间
	logMtime := ""
	if fi, err := os.Stat(logPath); err == nil {
		logMtime = fi.ModTime().Format("2006-01-02 15:04:05")
	}

	qMu.Lock()
	qs := qStatus
	qMu.Unlock()

	pd := PageData{
		Data:           items,
		AllLogFiles:    getAllLogFiles(),
		CurrentLogfile: logfile,
		CurrentSort:    sortBy,
		CurrentOrder:   order,
		UseCustomFont:  font == "enabled",
		Running:        qs.Running,
		QS:             qs,
		LogPath:        logPath,
		LogMtime:       logMtime,
	}

	c.Header("Content-Type", "text/html; charset=utf-8")
	tmpl.ExecuteTemplate(c.Writer, "index.html", pd)
}

func statusHandler(c *gin.Context) {
	qMu.Lock()
	defer qMu.Unlock()
	c.JSON(http.StatusOK, qStatus)
}

func locationsHandler(c *gin.Context) {
	ipsParam := c.Query("ips")
	result := make(map[string]map[string]string)
	for _, ip := range strings.Split(ipsParam, ",") {
		ip = strings.TrimSpace(ip)
		if ip == "" {
			continue
		}
		if loc, api, ok := dbGet(ip); ok {
			result[ip] = map[string]string{"location": loc, "api_source": api}
		}
	}
	c.JSON(http.StatusOK, result)
}

// ==================== main ====================

func main() {
	initDB()
	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()
	r.Static("/static", "./static")
	r.GET("/", indexHandler)
	r.GET("/status", statusHandler)
	r.GET("/locations", locationsHandler)
	log.Printf("Starting on :%s", port)
	r.Run(":" + port)
}
