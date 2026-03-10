/*
 * =============================================================
 *   IoT PET FEEDER - ESP32 Firmware
 *   Hardware: ESP32 + Servo Motor + Load Cell (HX711)
 *   Protocol: WiFi + MQTT (Mosquitto Broker)
 * =============================================================
 * 
 * MQTT Topics:
 *   Subscribe: petfeeder/command  (terima perintah dari server)
 *   Publish:   petfeeder/status   (kirim status perangkat)
 *              petfeeder/foodlevel (kirim level makanan)
 *              petfeeder/log      (kirim log aktivitas)
 *
 * Command Format (JSON):
 *   {"action": "feed", "amount": 50}    // feed manual
 *   {"action": "status"}                // minta status
 *   {"action": "calibrate"}             // kalibrasi sensor
 *
 * Status Format (JSON):
 *   {"device_id": "PF001", "online": true, "food_level": 75,
 *    "last_feed": "2026-03-09T22:00:00", "feeding_count": 5}
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include <time.h>

// ─── WiFi Configuration ───────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ─── MQTT Configuration ───────────────────────────────────────
const char* MQTT_BROKER   = "192.168.1.100";  // IP broker (server)
const int   MQTT_PORT     = 1883;
const char* MQTT_CLIENT_ID = "PetFeeder_ESP32_001";
const char* DEVICE_ID     = "PF001";

// ─── MQTT Topics ──────────────────────────────────────────────
const char* TOPIC_COMMAND   = "petfeeder/command";
const char* TOPIC_STATUS    = "petfeeder/status";
const char* TOPIC_FOODLEVEL = "petfeeder/foodlevel";
const char* TOPIC_LOG       = "petfeeder/log";

// ─── Pin Configuration ────────────────────────────────────────
const int SERVO_PIN        = 18;   // Servo motor pin
const int LOADCELL_DT      = 21;   // HX711 Data pin
const int LOADCELL_SCK     = 22;   // HX711 Clock pin
const int LED_STATUS       = 2;    // Built-in LED status
const int BUZZER_PIN       = 23;   // Buzzer for feeding notification

// ─── Feeder Configuration ─────────────────────────────────────
const int SERVO_OPEN_ANGLE  = 90;   // Servo angle when open
const int SERVO_CLOSE_ANGLE = 0;    // Servo angle when closed
const int FEED_DURATION_MS  = 2000; // How long to keep servo open (ms)
const float MAX_FOOD_WEIGHT = 500.0; // Max food capacity in grams

// ─── Global Variables ─────────────────────────────────────────
WiFiClient   espClient;
PubSubClient mqttClient(espClient);
Servo        feederServo;

float  currentFoodLevel = 75.0;   // Simulated food level %
int    feedingCount     = 0;
bool   isFeeding        = false;
String lastFeedTime     = "";
unsigned long lastStatusPublish = 0;
const unsigned long STATUS_INTERVAL = 30000; // Publish status every 30s

// ─── Function Prototypes ──────────────────────────────────────
void connectWiFi();
void connectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void triggerFeeding(int amount);
void publishStatus();
void publishFoodLevel();
void publishLog(String message);
float readFoodLevel();
String getTimestamp();

// ─── Setup ───────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n=== IoT Pet Feeder - ESP32 Starting ===");

  // Pin setup
  pinMode(LED_STATUS, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_STATUS, LOW);

  // Servo setup
  feederServo.attach(SERVO_PIN);
  feederServo.write(SERVO_CLOSE_ANGLE);

  // WiFi connect
  connectWiFi();

  // MQTT setup
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  connectMQTT();

  // NTP Time sync
  configTime(25200, 0, "pool.ntp.org"); // UTC+7 WIB
  Serial.println("=== System Ready ===\n");

  // Publish initial status
  publishStatus();
}

// ─── Main Loop ───────────────────────────────────────────────
void loop() {
  // Reconnect WiFi jika terputus
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Reconnect MQTT jika terputus
  if (!mqttClient.connected()) {
    connectMQTT();
  }

  mqttClient.loop();

  // Publish status setiap 30 detik
  unsigned long now = millis();
  if (now - lastStatusPublish > STATUS_INTERVAL) {
    lastStatusPublish = now;
    currentFoodLevel = readFoodLevel();
    publishStatus();
    publishFoodLevel();
  }

  delay(100);
}

// ─── WiFi Connect ─────────────────────────────────────────────
void connectWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected!");
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(LED_STATUS, HIGH);
  } else {
    Serial.println("\n[WiFi] Failed to connect!");
    digitalWrite(LED_STATUS, LOW);
  }
}

// ─── MQTT Connect ─────────────────────────────────────────────
void connectMQTT() {
  Serial.print("[MQTT] Connecting to broker...");

  // LWT (Last Will Testament) — pesan offline otomatis
  String lwtPayload = "{\"device_id\":\"" + String(DEVICE_ID) +
                      "\",\"online\":false}";

  while (!mqttClient.connected()) {
    if (mqttClient.connect(MQTT_CLIENT_ID, nullptr, nullptr, 
                           TOPIC_STATUS, 1, true, lwtPayload.c_str())) {
      Serial.println(" Connected!");
      // Subscribe ke topic command
      mqttClient.subscribe(TOPIC_COMMAND);
      Serial.println("[MQTT] Subscribed to: " + String(TOPIC_COMMAND));
    } else {
      Serial.print(".");
      delay(2000);
    }
  }
}

// ─── MQTT Message Callback ────────────────────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Parse payload
  char message[length + 1];
  memcpy(message, payload, length);
  message[length] = '\0';

  Serial.print("[MQTT] Received on [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  // Parse JSON command
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, message);
  if (error) {
    Serial.println("[Error] JSON parse failed");
    return;
  }

  String action = doc["action"].as<String>();

  if (action == "feed") {
    int amount = doc["amount"] | 50; // Default 50g
    if (!isFeeding) {
      Serial.println("[Feed] Manual feed triggered, amount: " + String(amount) + "g");
      publishLog("Manual feed triggered: " + String(amount) + "g");
      triggerFeeding(amount);
    } else {
      Serial.println("[Feed] Already feeding, ignoring command");
    }
  }
  else if (action == "status") {
    publishStatus();
    publishFoodLevel();
  }
  else if (action == "calibrate") {
    Serial.println("[Calibrate] Starting sensor calibration...");
    publishLog("Sensor calibration started");
    // Calibration logic here
  }
}

// ─── Trigger Feeding ──────────────────────────────────────────
void triggerFeeding(int amountGrams) {
  isFeeding = true;

  // Beep notification
  tone(BUZZER_PIN, 1000, 300);

  // Open servo
  Serial.println("[Servo] Opening feeder...");
  feederServo.write(SERVO_OPEN_ANGLE);

  // Calculate time based on amount (roughly 25g/s)
  int feedDuration = (amountGrams / 25.0) * 1000;
  feedDuration = constrain(feedDuration, 500, 5000);
  delay(feedDuration);

  // Close servo
  Serial.println("[Servo] Closing feeder...");
  feederServo.write(SERVO_CLOSE_ANGLE);

  // Update stats
  feedingCount++;
  lastFeedTime = getTimestamp();
  currentFoodLevel = max(0.0f, currentFoodLevel - (amountGrams / MAX_FOOD_WEIGHT * 100.0f));

  // Beep done
  delay(300);
  tone(BUZZER_PIN, 1500, 200);

  // Update dan publish status
  publishStatus();
  publishFoodLevel();
  publishLog("Feed completed: " + String(amountGrams) + "g at " + lastFeedTime);

  isFeeding = false;
  Serial.println("[Feed] Done!");
}

// ─── Read Food Level (HX711 Load Cell) ───────────────────────
float readFoodLevel() {
  // Simulasi pembacaan load cell HX711
  // Pada hardware nyata: gunakan library HX711
  // float weight = scale.get_units(5);
  // return (weight / MAX_FOOD_WEIGHT) * 100.0;
  
  // Simulasi: kurangi sedikit setiap pembacaan (degradasi natural)
  float simLevel = currentFoodLevel - random(0, 1);
  return constrain(simLevel, 0.0, 100.0);
}

// ─── Publish Status ───────────────────────────────────────────
void publishStatus() {
  StaticJsonDocument<512> doc;
  doc["device_id"]     = DEVICE_ID;
  doc["online"]        = true;
  doc["food_level"]    = (int)currentFoodLevel;
  doc["feeding_count"] = feedingCount;
  doc["last_feed"]     = lastFeedTime;
  doc["is_feeding"]    = isFeeding;
  doc["wifi_rssi"]     = WiFi.RSSI();
  doc["timestamp"]     = getTimestamp();

  char buffer[512];
  serializeJson(doc, buffer);
  mqttClient.publish(TOPIC_STATUS, buffer, true); // Retain = true
  Serial.println("[Status] Published: " + String(buffer));
}

// ─── Publish Food Level ───────────────────────────────────────
void publishFoodLevel() {
  StaticJsonDocument<128> doc;
  doc["device_id"]  = DEVICE_ID;
  doc["food_level"] = (int)currentFoodLevel;
  doc["timestamp"]  = getTimestamp();

  char buffer[128];
  serializeJson(doc, buffer);
  mqttClient.publish(TOPIC_FOODLEVEL, buffer);
}

// ─── Publish Log ──────────────────────────────────────────────
void publishLog(String message) {
  StaticJsonDocument<256> doc;
  doc["device_id"] = DEVICE_ID;
  doc["message"]   = message;
  doc["timestamp"] = getTimestamp();

  char buffer[256];
  serializeJson(doc, buffer);
  mqttClient.publish(TOPIC_LOG, buffer);
}

// ─── Get Timestamp (WIB / UTC+7) ─────────────────────────────
String getTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "1970-01-01T00:00:00";
  }
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", &timeinfo);
  return String(buffer);
}
