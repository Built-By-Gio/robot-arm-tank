#include <Bluepad32.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// ESP32-WROOM-32U DevKitC. ZK-5AD takes PWM straight on its IN pins, no enable pins.
const int A1_PIN = 25, A2_PIN = 26;
const int B1_PIN = 27, B2_PIN = 33;
const int SDA_PIN = 21, SCL_PIN = 22;
// TT motors are 3-6V and the pack is 8.4V full, ZK-5AD has no voltage drop
const int MAX_DUTY = 180;

// PCA9685 channels 0-6: base, shoulder (20kg), elbow, wrist, gripper, camera pan, camera tilt
Adafruit_PWMServoDriver servos;
const int N = 7;
const float HOME[N] = {90, 90, 90, 90, 90, 90, 90};
// arm folded over the hull for carrying; flip a value around 90 if that joint turns the wrong way
const float STOW[N] = {90, 165, 60, 60, 90, 90, 90};
const float LO[N] = {10, 30, 10, 10, 18, 0, 15};
const float HI[N] = {170, 170, 170, 170, 162, 180, 165};
const float SPEED[N] = {90, 60, 90, 120, 150, 120, 90};  // deg/s at full input

const int DEADZONE = 40;

ControllerPtr pad;
float pos[N];
unsigned long last;

void onConnected(ControllerPtr c) {
  if (!pad) pad = c;
}

void onDisconnected(ControllerPtr c) {
  if (pad == c) pad = nullptr;
}

void drive(int p1, int p2, int v) {
  v = constrain(v, -255, 255) * MAX_DUTY / 255;
  ledcWrite(p1, v > 0 ? v : 0);
  ledcWrite(p2, v < 0 ? -v : 0);
}

void writeServo(int i) {
  servos.writeMicroseconds(i, 500 + pos[i] * 2000 / 180);
}

int stick(int v) {
  if (abs(v) < DEADZONE) return 0;
  return v;
}

void setup() {
  Serial.begin(115200);
  for (int p : {A1_PIN, A2_PIN, B1_PIN, B2_PIN}) ledcAttach(p, 20000, 8);
  Wire.begin(SDA_PIN, SCL_PIN);
  servos.begin();
  servos.setOscillatorFrequency(27000000);
  servos.setPWMFreq(50);
  for (int i = 0; i < N; i++) {
    pos[i] = HOME[i];
    writeServo(i);
  }
  BP32.setup(&onConnected, &onDisconnected);
  last = millis();
}

void loop() {
  BP32.update();
  unsigned long now = millis();
  float dt = (now - last) / 1000.0;
  last = now;

  if (!pad || !pad->isConnected()) {
    drive(A1_PIN, A2_PIN, 0);
    drive(B1_PIN, B2_PIN, 0);
    delay(10);
    return;
  }

  int throttle = -stick(pad->axisY()) / 2;
  int turn = stick(pad->axisX()) / 2;
  drive(A1_PIN, A2_PIN, throttle + turn);
  drive(B1_PIN, B2_PIN, throttle - turn);

  float in[N];
  in[0] = -stick(pad->axisRX()) / 512.0;
  in[1] = -stick(pad->axisRY()) / 512.0;
  in[2] = (pad->r1() ? 1 : 0) - (pad->l1() ? 1 : 0);
  in[3] = ((pad->dpad() & DPAD_UP) ? 1 : 0) - ((pad->dpad() & DPAD_DOWN) ? 1 : 0);
  in[4] = (pad->throttle() - pad->brake()) / 1023.0;
  in[5] = ((pad->dpad() & DPAD_LEFT) ? 1 : 0) - ((pad->dpad() & DPAD_RIGHT) ? 1 : 0);
  in[6] = (pad->x() ? 1 : 0) - (pad->a() ? 1 : 0);

  if (pad->y()) {
    for (int i = 0; i < N; i++) pos[i] = HOME[i];
  }
  if (pad->b()) {
    for (int i = 0; i < N; i++) pos[i] = STOW[i];
  }
  if (pad->thumbR()) {
    pos[5] = HOME[5];
    pos[6] = HOME[6];
  }

  for (int i = 0; i < N; i++) {
    pos[i] = constrain(pos[i] + in[i] * SPEED[i] * dt, LO[i], HI[i]);
    writeServo(i);
  }

  delay(10);
}
