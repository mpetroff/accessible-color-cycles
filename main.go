package main

import (
	"encoding/base32"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/context"
	"github.com/gorilla/schema"
	"github.com/gorilla/securecookie"
	"github.com/gorilla/sessions"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

// Initialize secure cookie store
var (
	// TODO: load from environment variable
	// key must be 16, 24 or 32 bytes long (AES-128, AES-192 or AES-256)
	key   = []byte("super-secret-key")
	store = sessions.NewCookieStore(key)
)

// For decoding user responses
var decoder = schema.NewDecoder()

// For handling color set questions sent to user
type ColorSetQuestion struct {
	Set1     []string
	Set2     []string
	Orders   []string
	DrawMode int
	Picks    int
}

// For handling color set response from user
type ColorSetResponse struct {
	Set1      string
	Set2      string
	Orders    string
	DrawMode  int
	SetPick   int8
	OrderPick int8
}

// For handling questionnaire responses from user
type QuestionResponse struct {
	Consent           string
	ColorblindQ       string
	ColorblindTypeQ   string
	WindowWidth       int
	WindowOrientation string
}

// Reads and parses color sets file
func read_colors_txt(filename string) [][]string {
	csvFile, err := os.Open(filename)
	if err != nil {
		log.Fatal(err)
	}

	r := csv.NewReader(csvFile)
	r.Comma = ' '
	r.Comment = '#'
	r.TrimLeadingSpace = true
	records, err := r.ReadAll()
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println(len(records), "color sets read")

	return records
}

// Store parsed color sets
var color_sets_6 = read_colors_txt("colors_mcd20_mld2_nc6_cvd100_minj40_maxj90_ns10000_hsv_sorted.txt")
var len_color_sets_6 = int32(len(color_sets_6))
var color_sets_8 = read_colors_txt("colors_mcd18_mld2_nc8_cvd100_minj40_maxj90_ns10000_hsv_sorted.txt")
var len_color_sets_8 = int32(len(color_sets_8))
var color_sets_10 = read_colors_txt("colors_mcd16_mld2_nc10_cvd100_minj40_maxj90_ns10000_hsv_sorted.txt")
var len_color_sets_10 = int32(len(color_sets_10))

// Creates new user session for taking survey (deletes existing cookie)
func new_session(w http.ResponseWriter, r *http.Request) {
	session, _ := store.Get(r, "survey")
	session.Options.MaxAge = -1
	session.Save(r, w)
}

// Anonymize IP address by zeroing last bits
func anonymize_ip(ip string) string {
	pip := net.ParseIP(ip)
	if pip.DefaultMask() != nil {
		// IPv4
		mask := net.CIDRMask(24, 32)
		return pip.Mask(mask).String()
	} else {
		// IPv6
		mask := net.CIDRMask(32, 128)
		return pip.Mask(mask).String()
	}
}

// Handle survey responses from user
func colors(w http.ResponseWriter, r *http.Request) {
	session, _ := store.Get(r, "survey")

	// Find IP address of client
	ip, _, _ := net.SplitHostPort(r.RemoteAddr)
	fip := r.Header.Get("X-Forwarded-For")

	// Only record client IP address at last proxy
	fip = strings.SplitN(fip, ",", 1)[0]

	// Anonymize IP addresses
	ip = anonymize_ip(ip)
	fip = anonymize_ip(fip)

	// Make sure user has answered questionnaire
	if init := session.Values["id"]; init == nil {
		if r.Method == "POST" {
			// Parse response
			if err := r.ParseMultipartForm(1024); err != nil {
				http.Error(w, "Error parsing response", http.StatusInternalServerError)
				log.Println(err)
				return
			}
			qr := new(QuestionResponse)
			if err := decoder.Decode(qr, r.Form); err != nil {
				http.Error(w, "Error decoding response", http.StatusInternalServerError)
				log.Println(err)
				return
			}

			// Check for data collection consent
			if qr.Consent != "yes" {
				http.Error(w, "No consent", http.StatusInternalServerError)
				return
			}

			// Get user agent (and truncate)
			ua := r.Header.Get("User-Agent")
			if len(ua) > 100 {
				ua = ua[:100]
			}

			// Validate answers
			cbq := qr.ColorblindQ
			if cbq != "y" && cbq != "n" && cbq != "dk" && cbq != "dta" && cbq != "dna" {
				zap.L().Info("badanswer", zap.String("ip", ip), zap.String("fip", fip),
					zap.String("ua", ua), zap.String("n", "cbq"))
				http.Error(w, "Invalid answer", http.StatusInternalServerError)
				return
			}
			cbtq := qr.ColorblindTypeQ
			if cbtq != "na" && cbtq != "dta" && cbtq != "dk" && cbtq != "dy" &&
				cbtq != "py" && cbtq != "da" && cbtq != "pa" && cbtq != "ty" &&
				cbtq != "ta" && cbtq != "m" && cbtq != "o" && cbtq != "dna" {
				zap.L().Info("badanswer", zap.String("ip", ip), zap.String("fip", fip),
					zap.String("ua", ua), zap.String("n", "cbtq"))
				http.Error(w, "Invalid answer", http.StatusInternalServerError)
				return
			}
			orientation := qr.WindowOrientation
			if orientation != "l" && orientation != "p" {
				zap.L().Info("badanswer", zap.String("ip", ip), zap.String("fip", fip),
					zap.String("ua", ua), zap.String("n", "wo"))
				http.Error(w, "Invalid answer", http.StatusInternalServerError)
				return
			}

			// Create a random session ID
			session.Values["id"] = strings.TrimRight(
				base32.StdEncoding.EncodeToString(
					securecookie.GenerateRandomKey(32)), "=")

			// Initialize response counter
			session.Values["picks"] = 0

			// Log response
			zap.L().Info("session", zap.String("id", session.Values["id"].(string)),
				zap.String("ip", ip), zap.String("fip", fip), zap.String("ua", ua),
				zap.String("consent", qr.Consent),
				zap.String("cbq", cbq), zap.String("cbtq", cbtq),
				zap.Int("ww", qr.WindowWidth), zap.String("wo", orientation))
		} else {
			// Prompt for question answers
			w.Header().Set("Content-Type", "text/json; charset=utf-8")
			w.Write([]byte("{\"Question\": true}"))
			return
		}
	}

	// Randomly pick two color sets
	num_colors := 6 + rand.Intn(3) * 2
	var cycle1 []string
	var cycle2 []string
    if num_colors == 6 {
	    cycle1 = append([]string(nil), color_sets_6[rand.Int31n(len_color_sets_6)]...)
	    cycle2 = append([]string(nil), color_sets_6[rand.Int31n(len_color_sets_6)]...)
	} else if num_colors == 8 {
	    cycle1 = append([]string(nil), color_sets_8[rand.Int31n(len_color_sets_8)]...)
	    cycle2 = append([]string(nil), color_sets_8[rand.Int31n(len_color_sets_8)]...)
	} else {
	    cycle1 = append([]string(nil), color_sets_10[rand.Int31n(len_color_sets_10)]...)
	    cycle2 = append([]string(nil), color_sets_10[rand.Int31n(len_color_sets_10)]...)
	}

	// Randomly generate four permutations
	orders := [][]int{rand.Perm(num_colors), rand.Perm(num_colors), rand.Perm(num_colors), rand.Perm(num_colors)}
	var ordersStr []string
	for _, x := range orders {
		ordersStr = append(ordersStr, strings.Trim(strings.Replace(fmt.Sprint(x), " ", "", -1), "[]"))
	}

	// Randomly pick a drawing mode
	drawMode := rand.Intn(4)

	// Number of picks the user has made
	picks := session.Values["picks"].(int)

	// Retrieve previous information from cryptographically-signed cookie
	flashes := session.Flashes()

	// Parse, verify, and record response
	if r.Method == "POST" && len(flashes) > 0 {
		if err := r.ParseMultipartForm(1024); err != nil {
			http.Error(w, "Error parsing response", http.StatusInternalServerError)
			log.Println(err)
			return
		}
		csr := new(ColorSetResponse)
		if err := decoder.Decode(csr, r.Form); err != nil {
			http.Error(w, "Error decoding response", http.StatusInternalServerError)
			log.Println(err)
			return
		}
		if flashes[0] != csr.Set1+";"+csr.Set2+";"+csr.Orders+";"+strconv.Itoa(csr.DrawMode) {
			log.Printf("Bad match %s %s\n", flashes[0], csr.Set1+";"+csr.Set2+";"+csr.Orders+";"+strconv.Itoa(csr.DrawMode))
			zap.L().Info("badmatch", zap.String("id", session.Values["id"].(string)),
				zap.String("ip", ip), zap.String("fip", fip))
		} else {
			sp := csr.SetPick
			cp := csr.OrderPick
			if sp > 0 && sp <= 2 && cp > 0 && cp <= 4 {
				//log.Printf("Good match %s %s\n", flashes[0], csr.Set1 + ";" + csr.Set2)
				//log.Println("Pick", csr.Pick)
				zap.L().Info("pick", zap.String("id", session.Values["id"].(string)),
					zap.String("ip", ip), zap.String("fip", fip),
					zap.String("c1", csr.Set1), zap.String("c2", csr.Set2),
					zap.String("o", csr.Orders), zap.Int("dm", csr.DrawMode),
					zap.Int8("sp", sp), zap.Int8("cp", cp), zap.Int("np", picks))
				picks += 1
				session.Values["picks"] = picks
			} else {
				zap.L().Info("badpick", zap.String("id", session.Values["id"].(string)),
					zap.String("ip", ip), zap.String("fip", fip))
			}
		}
	}

	// Save generated sets, permutations, and drawing mode in session
	session.AddFlash(strings.Join(cycle1, ",") + ";" + strings.Join(cycle2, ",") + ";" + strings.Join(ordersStr, ",") + ";" + strconv.Itoa(drawMode))
	session.Save(r, w)

	// Encode JSON response with color cycles
	csq := ColorSetQuestion{cycle1, cycle2, ordersStr, drawMode, session.Values["picks"].(int)}
	w.Header().Set("Content-Type", "text/json; charset=utf-8")
	if err := json.NewEncoder(w).Encode(csq); err != nil {
		http.Error(w, "Error encoding JSON", http.StatusInternalServerError)
		return
	}
}

func main() {
	// Seed PRNG with current time
	rand.Seed(time.Now().UnixNano())

	// Set up logger to record results
	logger := zap.New(zapcore.NewCore(
		zapcore.NewJSONEncoder(zapcore.EncoderConfig{
			MessageKey: "type",
			TimeKey:    "ts",
			EncodeTime: zapcore.EpochTimeEncoder,
		}),
		zapcore.AddSync(&lumberjack.Logger{
			Filename: "results.log",
		}),
		zapcore.InfoLevel,
	))
	defer logger.Sync() // Flushes buffer, if any
	zap.ReplaceGlobals(logger)

	// Only send cookie to data endpoint, delete cookie when browser is closed,
	// and don't allow access from JavaScript
	store.Options = &sessions.Options{
		Path:     "/colors",
		MaxAge:   0,
		HttpOnly: true,
	}

	// Configure web server
	mux := http.NewServeMux()
	mux.HandleFunc("/colors", colors)
	mux.HandleFunc("/colors/new", new_session)
	mux.Handle("/", http.FileServer(http.Dir("static")))
	http.ListenAndServe(":8080", context.ClearHandler(mux))
}
