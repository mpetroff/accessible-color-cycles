package main

import (
	"encoding/base32"
	"encoding/csv"
	"encoding/hex"
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
	// Key must be 32 bytes long (AES-256)
	key, keyErr = hex.DecodeString(os.Getenv("SESSION_KEY"))
	store       = sessions.NewCookieStore(key)
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
func readColorsTxt(filename string) [][]string {
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
var colorSets6 = readColorsTxt("color-sets/colors_mcd20_mld2_nc6_cvd100_minj40_maxj90_ns10000_hsv_sorted.txt")
var lenColorSets6 = int32(len(colorSets6))
var colorSets8 = readColorsTxt("color-sets/colors_mcd18_mld2_nc8_cvd100_minj40_maxj90_ns10000_hsv_sorted.txt")
var lenColorSets8 = int32(len(colorSets8))
var colorSets10 = readColorsTxt("color-sets/colors_mcd16_mld2_nc10_cvd100_minj40_maxj90_ns10000_hsv_sorted.txt")
var lenColorSets10 = int32(len(colorSets10))

// Creates new user session for taking survey (deletes existing cookie)
func newSession(w http.ResponseWriter, r *http.Request) {
	session, _ := store.Get(r, "survey")
	session.Options.MaxAge = -1
	session.Save(r, w)
}

// Anonymize IP address by zeroing last bits
func anonymizeIP(ip string) string {
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
	//ip, _, _ := net.SplitHostPort(r.RemoteAddr)
	ip := r.Header.Get("X-Real-IP")

	// Anonymize IP addresses
	ip = anonymizeIP(ip)

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
				zap.L().Info("badanswer", zap.String("ip", ip),
					zap.String("ua", ua), zap.String("n", "cbq"))
				http.Error(w, "Invalid answer", http.StatusInternalServerError)
				return
			}
			cbtq := qr.ColorblindTypeQ
			if cbtq != "na" && cbtq != "dta" && cbtq != "dk" && cbtq != "dy" &&
				cbtq != "py" && cbtq != "da" && cbtq != "pa" && cbtq != "ty" &&
				cbtq != "ta" && cbtq != "m" && cbtq != "o" && cbtq != "dna" {
				zap.L().Info("badanswer", zap.String("ip", ip),
					zap.String("ua", ua), zap.String("n", "cbtq"))
				http.Error(w, "Invalid answer", http.StatusInternalServerError)
				return
			}
			orientation := qr.WindowOrientation
			if orientation != "l" && orientation != "p" {
				zap.L().Info("badanswer", zap.String("ip", ip),
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
				zap.String("ip", ip), zap.String("ua", ua),
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

	// Retrieve previous information from cryptographically-signed cookie
	flashes := session.Flashes()

	// User reloaded page (present previous choices using cookie)
	if r.Method == "GET" && len(flashes) > 0 {
		// Save generated sets, permutations, and drawing mode in session
		session.AddFlash(flashes[0])
		session.Save(r, w)

		// Encode JSON response with color cycles
		flashData := strings.Split(flashes[0].(string), ";")
		drawMode, _ := strconv.Atoi(flashData[3])
		csq := ColorSetQuestion{strings.Split(flashData[0], ","),
			strings.Split(flashData[1], ","),
			strings.Split(flashData[2], ","),
			drawMode, session.Values["picks"].(int)}
		w.Header().Set("Content-Type", "text/json; charset=utf-8")
		if err := json.NewEncoder(w).Encode(csq); err != nil {
			http.Error(w, "Error encoding JSON", http.StatusInternalServerError)
			return
		}

		return
	}

	// Randomly pick two color sets
	numColors := 6 + rand.Intn(3)*2
	var cycle1 []string
	var cycle2 []string
	if numColors == 6 {
		cycle1 = append([]string(nil), colorSets6[rand.Int31n(lenColorSets6)]...)
		cycle2 = append([]string(nil), colorSets6[rand.Int31n(lenColorSets6)]...)
	} else if numColors == 8 {
		cycle1 = append([]string(nil), colorSets8[rand.Int31n(lenColorSets8)]...)
		cycle2 = append([]string(nil), colorSets8[rand.Int31n(lenColorSets8)]...)
	} else {
		cycle1 = append([]string(nil), colorSets10[rand.Int31n(lenColorSets10)]...)
		cycle2 = append([]string(nil), colorSets10[rand.Int31n(lenColorSets10)]...)
	}

	// Randomly generate four permutations
	orders := [][]int{rand.Perm(numColors), rand.Perm(numColors), rand.Perm(numColors), rand.Perm(numColors)}
	var ordersStr []string
	for _, x := range orders {
		ordersStr = append(ordersStr, strings.Trim(strings.Replace(fmt.Sprint(x), " ", "", -1), "[]"))
	}

	// Randomly pick a drawing mode
	drawMode := rand.Intn(4)

	// Number of picks the user has made
	picks := session.Values["picks"].(int)

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
				zap.String("ip", ip))
		} else {
			sp := csr.SetPick
			cp := csr.OrderPick
			if sp > 0 && sp <= 2 && cp > 0 && cp <= 4 {
				//log.Printf("Good match %s %s\n", flashes[0], csr.Set1 + ";" + csr.Set2)
				//log.Println("Pick", csr.Pick)
				zap.L().Info("pick", zap.String("id", session.Values["id"].(string)),
					zap.String("ip", ip),
					zap.String("c1", csr.Set1), zap.String("c2", csr.Set2),
					zap.String("o", csr.Orders), zap.Int("dm", csr.DrawMode),
					zap.Int8("sp", sp), zap.Int8("cp", cp), zap.Int("np", picks))
				picks += 1
				session.Values["picks"] = picks
			} else {
				zap.L().Info("badpick", zap.String("id", session.Values["id"].(string)),
					zap.String("ip", ip))
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
	// Make sure session key is loaded
	if keyErr != nil {
		log.Fatal(keyErr)
	}
	if len(key) != 32 {
		log.Fatal("Session key must be 32 bytes!")
	}

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
	mux.HandleFunc("/colors/new", newSession)
	mux.Handle("/", http.FileServer(http.Dir("static")))
	http.ListenAndServe(":8080", context.ClearHandler(mux))
}
