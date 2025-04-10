/*********
  Rui Santos & Sara Santos - Random Nerd Tutorials
  Modified from the examples of the Arduino LoRa library
  More resources: https://RandomNerdTutorials.com/
esp32-lora-rfm95-transceiver-arduino-ide/
*********/

#include <Arduino.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "SD_card.h"
#include "CAN_functions.h"
#include "LoRa_functions.h"

// Flag for writing in same folder on the SD-card
int SDcardFlag = 1;

// Variables for blinking LEDs
int count = 0;
unsigned long previousMillisLEDs = 0;
const int blinkInterval = 500;
bool ledState = LOW;

void prepareAndWrite2SD() {
  char buffer[512];
  snprintf(buffer, sizeof(buffer),
            "%.2f %.2f "
            "%.2f %.2f "
            "%.2f %.2f %.2f "
            "%.2f %.2f %.2f "
            "%.2f %.2f %.2f "
            "%.2f %.2f %.2f "
            "%.2f %.2f %.2f %.2f \n",
            velocity, distance_travelled, 
            battery_volt, battery_current, 
            battery_cell_LOW_volt, battery_cell_HIGH_volt, battery_cell_AVG_volt,
            battery_cell_LOW_temp, battery_cell_HIGH_temp, battery_cell_AVG_temp,
            battery_cell_ID_HIGH_temp, battery_cell_ID_LOW_temp, BMS_temp,
            motor_current, motor_temp, motor_controller_temp,
            MPPT1_watt, MPPT2_watt, MPPT3_watt, MPPT_total_watt);
  
  digitalWrite(SS, HIGH);           // Deselect LoRa
  digitalWrite(CS, LOW);            // Select SD card
  write2SDcard(buffer, SDcardFlag); // Write file to SD card
  if(SDcardFlag) SDcardFlag = 0;    // Set flag to 0 after first iteration to write on the same file
  digitalWrite(CS, HIGH);           // Deselect SD card
  digitalWrite(SS, LOW);            // Select LoRa
}

void blinkLEDs() {

  unsigned long currentMillis = millis();

  if(currentMillis - previousMillisLEDs >= blinkInterval) {
    previousMillisLEDs = currentMillis;
    ledState = !ledState;

    // Blink LEDS
    if (left_blinker > 0.0 || hazard_light > 0.0) {
    digitalWrite(15, ledState);
    }
    else
      digitalWrite(15, LOW);
    
    if (right_blinker > 0.0 || hazard_light > 0.0) {
      digitalWrite(16, ledState);
    }
    else
      digitalWrite(16, LOW);
    
    if (brake_light > 0.0) {
      digitalWrite(7, HIGH);
    }
    else
      digitalWrite(7, LOW);
  }
}

void setup() {

  //initialize Serial Monitor
  Serial.begin(115200);
  while (!Serial);

  setupLoRa();

  setupCAN();

  Serial.println("Pin Configuration:");
  Serial.print("SS: "); Serial.println(SS);
  Serial.print("RST: "); Serial.println(RST);
  Serial.print("DIO0: "); Serial.println(DIO0);
  Serial.print("SCK: "); Serial.println(SCK);
  Serial.print("MISO: "); Serial.println(MISO);
  Serial.print("MOSI: "); Serial.println(MOSI);
  Serial.print("CS: "); Serial.println(CS);

  // Initialize SD
  if(!SD.begin(CS, spiLoRa)) {
    Serial.println("SD Card Mount Failed");
  } else {
    Serial.println("SD Card Mount Succesful");
  }

  // Initialize NVS
  if (initNVS()) {
    Serial.println("NVS Initialized");
  } else {
    Serial.println("NVS Initialization Failed");
  }

  // Blinkers setup
  pinMode(15, OUTPUT);
  digitalWrite(15, LOW);
  pinMode(16, OUTPUT);
  digitalWrite(16, LOW);
  pinMode(7, OUTPUT);
  digitalWrite(7, LOW);
}

void loop() {

  static clock_t lastSendTime = 0;
  if (ESP32Can.readFrame(msg, 0)) {
    Serial.print("+");
    //Serial.printf("Received CAN ID: %3X \r\n", msg.identifier);

    // Assign CAN data to specified variable based on identifier
    assignCAN2variable();

    //Blink LEDs
    blinkLEDs();

    clock_t currentTime = clock();
    double timeElapsed = ((double)(currentTime - lastSendTime))/CLOCKS_PER_SEC;

    if (timeElapsed >= sendInterval) {

      Serial.println();

      /* //Print information form driver
      if(driver_current > 0.0 || driverRPM > 0.0) {
        Serial.printf("Driver current: %.2f, Driver RPM: %.2f", driver_current, driverRPM);
        Serial.println();
      }
      if(left_blinker > 0 || right_blinker > 0 || hazard_light > 0 || brake_light > 0) {
        Serial.printf("left: %d, right %d, hazard: %d, brake: %d", left_blinker, right_blinker, hazard_light, brake_light);
        Serial.println();
      } */

      // Prepare const char of our variables and save to SD card
      prepareAndWrite2SD();

      // Send with LoRa
      sendLoRaData();

      lastSendTime = currentTime;
    }
  }

  // Check for incoming parameters from receiver
  /* int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String receivedParams = "";
    while (LoRa.available()) {
      receivedParams += (char)LoRa.read();
    }
    if (receivedParams.startsWith("PARAM")) {
      int sfIndex = receivedParams.indexOf(' ', 6);
      int sbwIndex = receivedParams.indexOf(' ', sfIndex + 1);
      sf = receivedParams.substring(6, sfIndex).toInt();
      sbw = receivedParams.substring(sfIndex + 1, sbwIndex).toInt();

      LoRa.setSpreadingFactor(sf);
      LoRa.setSignalBandwidth(sbw);

      Serial.printf("Updated SF: %d, SBW: %ld\n", sf, sbw);
    }
  } */
}
