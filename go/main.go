package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3"
)

var db *sql.DB
var queryStatus struct {
	Total   int
	Done    int
	Running bool
	mu     sync.RWMutex
}
var locationCache = make(map[string]string)
var cacheMu sync.RWMutex

type LogItem struct {
	IP       string
	Count    int
	Location string
	Status   string
}

func main() {
	initDB()
	
	r := gin.Default()
	
	// 静态文件
	r.Static("/static", "./static")
	
	// 首页
	r.GET("/", func(c *gin.Context) {
		c.File("index.html")
	})
	
	// API
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
		
		// 填充属地
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
		
		// 后台查询
		queryStatus.mu.Lock()
		running := queryStatus.Running
		queryStatus.mu.Unlock()
		
		if len(pendingIPs) > 0 && !running {
			go queryIPsBackground(pendingIPs)
		}
		
		queryStatus.mu.Lock()
		st := queryStatus
		queryStatus.mu.Unlock()
		
		c.JSON(http.StatusOK, gin.H{
			"data": items,
			"status": st,
		})
	})
	
	r.GET("/api/status", func(c *gin.Context) {
		queryStatus.mu.Lock()
		defer queryStatus.mu.Unlock()
		c.JSON(http.StatusOK, queryStatus)
	})
	
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("Server starting on :%s", port)
	r.Run(":" + port)
}

func initDB() {
	var err error
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "data.db"
	}
	db, err = sql.Open("sqlite3", dbPath)
	if err != nil {
		log.Fatal(err)
	}
	
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS access_log (
		ip TEXT PRIMARY KEY,
		count INTEGER DEFAULT 1,
		last_time TEXT
	)`)
	if err != nil {
		log.Fatal(err)
	}
	
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS location_cache (
		ip TEXT PRIMARY KEY,
		location TEXT,
		last_time TEXT
	)`)
	if err != nil {
		log.Fatal(err)
	}
	
	// 加载缓存
	rows, _ := db.Query("SELECT ip, location FROM location_cache")
	if rows != nil {
		for rows.Next() {
			var ip, loc string
			rows.Scan(&ip, &loc)
			cacheMu.Lock()
			locationCache[ip] = loc
			cacheMu.Unlock()
		}
		rows.Close()
	}
}

func getLogData() []LogItem {
	rows, err := db.Query("SELECT ip, count FROM access_log ORDER BY count DESC")
	if err != nil {
		return nil
	}
	defer rows.Close()
	
	var items []LogItem
	for rows.Next() {
		var item LogItem
		rows.Scan(&item.IP, &item.Count)
		items = append(items, item)
	}
	return items
}

func getCachedLocation(ip string) (string, bool) {
	cacheMu.RLock()
	defer cacheMu.RUnlock()
	loc, ok := locationCache[ip]
	return loc, ok
}

func saveLocation(ip, location string) {
	cacheMu.Lock()
	locationCache[ip] = location
	cacheMu.Unlock()
	
	db.Exec("INSERT OR REPLACE INTO location_cache (ip, location, last_time) VALUES (?, ?, ?)",
		ip, location, time.Now().Format("2006-01-02 15:04:05"))
}

func queryIPsBackground(ips []string) {
	queryStatus.mu.Lock()
	queryStatus.Running = true
	queryStatus.Total = len(ips)
	queryStatus.Done = 0
	queryStatus.mu.Unlock()
	
	for _, ip := range ips {
		loc := fetchLocation(ip)
		saveLocation(ip, loc)
		
		queryStatus.mu.Lock()
		queryStatus.Done++
		queryStatus.mu.Unlock()
	}
	
	queryStatus.mu.Lock()
	queryStatus.Running = false
	queryStatus.mu.Unlock()
}

func fetchLocation(ip string) string {
	if strings.HasPrefix(ip, "192.168.") || strings.HasPrefix(ip, "10.") || strings.HasPrefix(ip, "172.") {
		return "内网IP"
	}
	
	// 简化处理，直接返回空
	return ""
}