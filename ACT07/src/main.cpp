#include <Servo.h>
#include <Arduino.h>

Servo myServo;
const int servoPin = 9;

void setup() {
  Serial.begin(9600);
  myServo.attach(servoPin);
  
  // Set initial position to 0
  myServo.write(0);
  Serial.println("Arduino Ready. Send 0-180.");
}

void loop() {
  if (Serial.available() > 0) {
    String inputString = Serial.readStringUntil('\n');
    inputString.trim();

    if (inputString.length() > 0) {
      int degrees = inputString.toInt();

      if (degrees >= 0 && degrees <= 180) {
        myServo.write(degrees);
        Serial.print("Moving to: ");
        Serial.println(degrees);
      } else {
        Serial.println("Error: Out of range (0-180)");
      }
    }
  }
}