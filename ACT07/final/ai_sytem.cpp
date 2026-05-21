#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ─────────────────────────────────────────────
//  HARDWARE CONFIG
// ─────────────────────────────────────────────
LiquidCrystal_I2C lcd(0x27, 16, 2);

const int TRIG1  = 9;
const int ECHO1  = 8;
const int TRIG2  = 7;
const int ECHO2  = 6;
const int BUZZER = 4;

// ─────────────────────────────────────────────
//  SPEED SETTINGS
// ─────────────────────────────────────────────
const float PATH_DISTANCE_M = 0.50;   // metres between the two sensors
const float SPEED_WARN      = 2.00;   // m/s  → WARNING threshold
const float SPEED_DANGER    = 3.00;   // m/s  → DANGER  threshold

// ─────────────────────────────────────────────
//  TIMING & STATE
// ─────────────────────────────────────────────
unsigned long t1            = 0;
unsigned long t2            = 0;
bool          started       = false;

unsigned long lastDetection = 0;
const unsigned long COOLDOWN_MS = 1500;   // ignore re-triggers for 1.5 s

// ─────────────────────────────────────────────
//  AI COMMAND STATE
// ─────────────────────────────────────────────
String aiCommand = "";
bool   alarmMode = false;

// ─────────────────────────────────────────────
//  FORWARD DECLARATIONS
// ─────────────────────────────────────────────
long  readDistance(int trig, int echo);
void  sendToAI(float speed, const String& status);
void  updateLCD(const String& l1, const String& l2);
void  handleAlarmTone();

// ─────────────────────────────────────────────
//  SENSOR
// ─────────────────────────────────────────────
long readDistance(int trig, int echo) {
  // Clean trigger pulse
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);

  // Wait up to 30 ms for echo (covers ~5 m)
  long duration = pulseIn(echo, HIGH, 30000UL);
  if (duration == 0) return 999;

  long cm = duration * 0.034 / 2;
  if (cm <= 0 || cm > 200) return 999;
  return cm;
}

// ─────────────────────────────────────────────
//  SERIAL → Python AI
// ─────────────────────────────────────────────
void sendToAI(float speed, const String& status) {
  // Format: TIME=<ms>|SPEED=<m/s>|STATUS=<label>
  Serial.print("TIME=");
  Serial.print(millis());
  Serial.print("|SPEED=");
  Serial.print(speed, 3);
  Serial.print("|STATUS=");
  Serial.println(status);
}

// ─────────────────────────────────────────────
//  LCD HELPER  (pads to 16 chars automatically)
// ─────────────────────────────────────────────
void updateLCD(const String& l1, const String& l2) {
  lcd.setCursor(0, 0);
  String row1 = l1 + "                ";
  lcd.print(row1.substring(0, 16));

  lcd.setCursor(0, 1);
  String row2 = l2 + "                ";
  lcd.print(row2.substring(0, 16));
}

// ─────────────────────────────────────────────
//  BUZZER HELPERS
// ─────────────────────────────────────────────
void handleAlarmTone() {
  static unsigned long lastTone = 0;
  if (millis() - lastTone > 200) {
    tone(BUZZER, 4000, 150);
    lastTone = millis();
  }
}

// ─────────────────────────────────────────────
//  SETUP
// ─────────────────────────────────────────────
void setup() {
  Serial.begin(9600);

  lcd.init();
  lcd.backlight();

  pinMode(TRIG1,  OUTPUT);
  pinMode(ECHO1,  INPUT);
  pinMode(TRIG2,  OUTPUT);
  pinMode(ECHO2,  INPUT);
  pinMode(BUZZER, OUTPUT);

  updateLCD("SMART SPEED", "AI READY");
  tone(BUZZER, 1000, 200);   // startup beep
  delay(500);
}

// ─────────────────────────────────────────────
//  LOOP
// ─────────────────────────────────────────────
void loop() {

  // ── 1. READ INCOMING AI COMMANDS ──────────
  if (Serial.available() > 0) {
    aiCommand = Serial.readStringUntil('\n');
    aiCommand.trim();

    if (aiCommand == "TRIGGER_ALARM") {
      alarmMode = true;
      tone(BUZZER, 3000, 500);
      updateLCD("!! AI ALERT !!", "ALARM ACTIVE");

    } else if (aiCommand == "CLEAR_ALARM") {
      alarmMode = false;
      updateLCD("SMART SPEED", "AI READY");

    } else if (aiCommand == "IGNORE") {
      alarmMode = false;

    } else if (aiCommand == "PING") {
      Serial.println("PONG");          // heartbeat reply
    }
  }

  // ── 2. ALARM MODE TONE (non-blocking) ─────
  if (alarmMode) {
    handleAlarmTone();
    return;   // skip speed detection while alarm is active
  }

  // ── 3. COOLDOWN GUARD ─────────────────────
  if (millis() - lastDetection < COOLDOWN_MS) return;

  // ── 4. SENSOR 1 — START GATE ──────────────
  long d1 = readDistance(TRIG1, ECHO1);

  if (!started && d1 < 10) {
    t1      = millis();
    started = true;
    tone(BUZZER, 2000, 80);
    updateLCD("TIMING...", "Sensor 1 OK");
    return;
  }

  // ── 5. SENSOR 2 — END GATE ────────────────
  if (started) {
    // Safety timeout: if nothing crosses S2 within 8 s, reset
    if (millis() - t1 > 8000UL) {
      started = false;
      updateLCD("TIMEOUT", "Try again");
      return;
    }

    long d2 = readDistance(TRIG2, ECHO2);

    if (d2 < 10) {
      t2 = millis();
      float timeSec = (t2 - t1) / 1000.0f;

      if (timeSec > 0.05f && timeSec < 8.0f) {

        float speed = PATH_DISTANCE_M / timeSec;   // m/s

        String status;
        if      (speed < SPEED_WARN)   status = "SAFE";
        else if (speed < SPEED_DANGER) status = "WARNING";
        else                           status = "DANGER";

        // Buzzer feedback
        if      (status == "SAFE")    tone(BUZZER, 1500, 100);
        else if (status == "WARNING") { tone(BUZZER, 2500, 200); delay(250); tone(BUZZER, 2500, 200); }
        else                          { tone(BUZZER, 4000, 400); delay(450); tone(BUZZER, 4000, 400); }

        // Display: row1 = status, row2 = speed in m/s
        String speedStr = String(speed, 2) + " m/s";
        updateLCD(status, speedStr);

        // Send to Python AI agent
        sendToAI(speed, status);

      } else {
        updateLCD("MEAS ERROR", "Retrying...");
        Serial.println("TIME=0|SPEED=0|STATUS=ERROR");
      }

      started        = false;
      lastDetection  = millis();
    }
  }
}