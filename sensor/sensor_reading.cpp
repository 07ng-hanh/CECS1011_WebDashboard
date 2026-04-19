// LIBS
#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <ScioSense_ENS16x.h>

// SET PINS
#define I2C_SDA 21
#define I2C_SCL 22
#define I2C_ADDRESS 0x52
#define INTN 2

// DEFINE SENSORS
Adafruit_AHTX0 aht;
ENS160 ens16x;

bool ensReady = false; 

void setup() {
  Serial.begin(115200);
  Wire.begin(I2C_SDA, I2C_SCL);

  // AHT21 AVAILABILITY
  if (aht.begin()) {
    Serial.println("AHT21 READY.");
  } else {
    Serial.println("AHT21 NOT FOUND.");
  }
  
  // ENS160 AVAILABILITY
  ens16x.begin(&Wire, I2C_ADDRESS); 
  
  // Check connection after begin
  if (ens16x.isConnected()) {
    Serial.println("ENS160 READY.");
    ensReady = true;
    ens16x.setInterruptPin(INTN);
    ens16x.startStandardMeasure();
  } else {
    Serial.println("ENS160 NOT FOUND. Switching to Random Mode.");
    ensReady = false;
  }
}

void loop() {
  // --- AHT21 READING ---
  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp);
  
  Serial.print("TEMP: "); Serial.print(temp.temperature);
  Serial.print(" | HUM: "); Serial.print(humidity.relative_humidity);
  Serial.print(" | ");

  // --- ENS160 READING ---
  uint16_t eco2Value;

  if (ensReady) {
    // Check if new data is available
    if (ens16x.available()) {
        eco2Value = ens16x.getEco2(); // Using getEco2 as suggested by compiler
        Serial.print("ENS160 eCO2: ");
        Serial.println(eco2Value);
    } else {
        Serial.println("ENS160: Waiting for data...");
    }
  } else {
    // Generate random number in range 850-1000
    eco2Value = random(850, 1001); 
    Serial.print("SIMULATED eCO2: ");
    Serial.println(eco2Value);
  }
  
  delay(2000); 
}
