# Robot Arm Tank: full setup and assembly guide

Work through this top to bottom. Each step says what you need and how to know it worked before moving on.
The visual overview is in `2_BUILD_PROCESS.html` (open it in a browser).

> The arm is DBI's P-P 1.2, scaled down. DBI's files are shared in this repo with DBI's permission (credit in the main README).
> Keep DBI's own PDF instructions open (they come with DBI's files and are not in this repo); this guide says where my build differs.
> The firmware this guide describes (with the `GEAR` mapping) is not in this repo yet; `firmware/` at the repo root is for the lattice arm.

---

## 0. Before you start

### Tools
- 3D printer (PLA + TPU)
- side cutters, small Phillips screwdriver, 2.5 mm hex key (M3), tweezers
- a USB-C cable that does **data** (not charge-only), a PC with the Arduino IDE
- an 18650 charger
- No soldering iron needed anywhere.

### Parts check: tick these off when the boxes arrive

| ✓ | Part | Qty | Goes where |
|---|---|---|---|
| ☐ | ESP32-WROOM-32U DevKitC (+ antenna) | 1 | tank brain, talks to the PS5 controller |
| ☐ | XIAO ESP32-S3 Sense (camera + board) | 1 | camera on the mast |
| ☐ | 6dBi antenna + U.FL pigtail | 2 | 1 on the camera (1 spare) |
| ☐ | MG90S servo | 6 | base, elbow, wrist, claw, camera pan, camera tilt |
| ☐ | SG90 servo (you have it) | 1 | shoulder |
| ☐ | PCA9685 servo board (you have it) | 1 | drives all 7 servos |
| ☐ | 6705ZZ bearing | 7 of 10 | 2 per arm joint + 1 in the base top |
| ☐ | Servo extension cables | as needed | arm + mast servo leads |
| ☐ | ZK-5AD motor driver | 1 of 2 | drive motors |
| ☐ | XL4015 buck converter | 1 | battery 7.4V to 5.1V |
| ☐ | USB-C screw-terminal adapter | 1 of 5 | powers the camera |
| ☐ | Samsung 25R 18650 | 2 of 4 | battery |
| ☐ | 2S 18650 holder | 1 of 2 | battery |
| ☐ | KCD1 pre-wired switch | 1 of 5 | power switch |
| ☐ | 3-port lever connectors | ~6 | all power joins |
| ☐ | E-clips (assortment) | 3 | one per arm joint shaft |
| ☐ | 4x TT motors with leads | 4 | wheels |
| ☐ | M3 screws + nuts, Dupont jumpers, velcro, foam tape, 1000uF cap | — | assorted |
| ☐ | PS5 DualSense, phone | — | control + video |

**Check the battery cells:** real Samsung 25R are green, flat-top, ~45 g, printed `INR18650-25R`. Return anything light or misprinted.
**Check the PCA9685:** its pin headers must already be soldered. If loose pins came in the bag, don't solder them; get a pre-soldered board.

---

## 1. Print everything (do this first, it takes the longest)

All files are in `stl/`. PLA unless it says TPU.

**Arm:** keep DBI's orientation (place them like DBI's PDF shows), supports on.

| File | Qty | Settings |
|---|---|---|
| arm_unten, arm_mitte, arm_oben | 1, 2, 1 | 3 walls, 10% infill (keep the arm light for the mini servos) |
| arm_mitte_cover, arm_oben_cover, arm_grip_cover | 2, 1, 1 | 3 walls, 10% |
| arm_base_lower, arm_base_upper | 1 each | 3 walls, 15% |
| arm_base_gear | 1 | 30% |
| arm_ring | 3 | 30%, 0.12 mm layers |
| arm_joint_gear | 3 | 100%, 0.12 mm layers |
| arm_grip_gear, arm_grip_pinion, arm_jaw | 1, 1, 2 | 100%, 0.12 mm layers |

**Tank:**

| File | Qty | Settings |
|---|---|---|
| tub, lid | 1 each | 3 walls, 15% |
| fender | 2 | mirror one in the slicer |
| clamp | 2 | mirror one |
| mast | 1 | servo block down, no supports |
| mast_base, knob, pan_yoke, cam_head | 1 each | flat side down |
| wheel | 4 | (or use the stock TT wheels) |
| tire | 4 | **TPU** |

**Check:** test-fit a 6705ZZ in a joint seat and an MG90S in a pocket before printing the rest. If tight, scale that part 100.5%; if loose, wrap tape (DBI's own tip).

---

## 2. Set up the software (before wiring anything)

### 2a. Tank firmware: ESP32-WROOM-32U
1. Install the Arduino IDE.
2. **File → Preferences → Additional boards manager URLs**, add:
   `https://raw.githubusercontent.com/ricardoquesada/esp32-arduino-lib-builder/master/bluepad32_files/package_esp32_bluepad32_index.json`
3. **Boards Manager:** install **ESP32 + Bluepad32**. **Library Manager:** install **Adafruit PWM Servo Driver**.
4. Open `firmware/arm_tank/arm_tank.ino`, board **ESP32 Dev Module**, plug in the ESP32, **Upload**.
5. **Check:** Serial Monitor (115200) shows the Bluepad32 banner.

### 2b. Camera firmware: XIAO ESP32-S3 Sense
1. Clip the camera board onto the XIAO (it snaps on; no solder) and screw the antenna pigtail onto the U.FL jack.
2. Board **XIAO_ESP32S3**, **PSRAM: OPI PSRAM**. Open `firmware/camera/camera.ino`.
3. Change `PASS` in the sketch to your own password (8+ characters). Upload.
4. **Check:** on your phone, join Wi-Fi `armtank-cam`, open `http://192.168.4.1`. You should see live video.

### 2c. Pair the PS5 controller
1. Power the ESP32 (USB is fine for now).
2. On the DualSense hold **Create + PS** until the light bar flashes fast.
3. **Check:** the light bar goes solid and the Serial Monitor says a controller connected. It remembers the pairing after this.

---

## 3. Build the hull

1. **Motors:** drop each TT motor into the tub, shaft through the wall slot, gearbox end under the end lip. Foam tape under the clamp, screw the clamp onto the post just inboard of the motors (M3). Both left motors' leads together, both right motors' leads together.
2. **Switch:** push the KCD1 into the front-wall cutout.
3. **Bay layout** (velcro): battery holder along the rear, XL4015 and ZK-5AD on top of it, ESP32 front-left pins up, PCA9685 front-right.
4. **Antenna:** controller antenna's SMA bulkhead in the lid's rear-right hole, pigtail to the ESP32's U.FL jack.
5. **Wheels:** TPU tires onto the wheels, wheels onto the shafts.

---

## 4. Wire it (no solder)

**Do step 4.1 with no battery cells in the holder.**

### 4.1 Set the buck converter first
1. Battery holder leads into the XL4015 **IN+ / IN−**.
2. Put the cells in, and turn the XL4015's little screw until its display reads **5.1 V**. Take the cells out again.
3. **Check:** 5.1 V. Never connect the servo board or the ESP32 until this reads 5.1 V; a fresh pack is 8.4 V.

### 4.2 Power (lever connectors)

| Connector | Wires in it |
|---|---|
| A (battery +) | switch output, ZK-5AD VCC, XL4015 IN+ |
| B (battery −) | battery −, ZK-5AD GND, XL4015 IN− |
| C (5V) | XL4015 OUT+, PCA9685 V+, short jumper to D |
| D (5V) | jumper from C, ESP32 **5V** pin, USB-C adapter + |
| E (GND) | XL4015 OUT−, PCA9685 GND, short jumper to F |
| F (GND) | jumper from E, ESP32 GND, USB-C adapter − |

Battery + goes through the switch first (battery + → switch → connector A).
The **1000uF capacitor** goes in the PCA9685's V+/GND screw terminal: long leg to **+**.

### 4.3 Signal (Dupont jumpers)

| From | To |
|---|---|
| ESP32 3V3 / GND | PCA9685 VCC / GND |
| ESP32 GPIO21 / GPIO22 | PCA9685 SDA / SCL |
| ESP32 GPIO25 / 26 | ZK-5AD IN1 / IN2 (left motors) |
| ESP32 GPIO27 / 33 | ZK-5AD IN3 / IN4 (right motors) |
| ZK-5AD MOTOR-A / MOTOR-B | left motor pair / right motor pair |

### 4.4 Servo channels on the PCA9685

| Ch | Servo |
|---|---|
| 0 | base (MG90S, in the lid) |
| 1 | shoulder (SG90) |
| 2 | elbow |
| 3 | wrist |
| 4 | claw |
| 5 | camera pan |
| 6 | camera tilt |

Brown/black wire = GND row, red = V+, orange/yellow = signal.

**Check:** power up with the switch. The ESP32 LED comes on, the XL4015 shows 5.1 V, and with the controller paired the left stick spins the wheels. If a side goes backwards, swap that motor pair's two wires at the ZK-5AD.

---

## 5. Servo prep (all arm servos)

1. Plug each servo into its channel and power up **with no horns on**: the firmware sends every servo to 90.
2. For each **arm** servo (the SG90 and the arm MG90S): snip the mounting tab off the **shaft end** with side cutters. Keep the far tab.
3. Cut a single-arm horn down to the round hub plus a ~2 mm stub (you need 4 of these: 3 joint gears + the claw gear, and one for the base gear).
4. **Don't turn any servo by hand** after this; set positions by powering to 90.

---

## 6. Build the base

1. Base servo (MG90S) into the lid's servo slot, tabs on top of the lid, M2 screws.
2. Bolt **arm_base_lower** onto the lid with 4x M3x10 and nuts under the lid. The servo top pokes up inside it.
3. Cut-down horn onto the base servo (at 90). Press **arm_base_gear** onto the horn, turned so that once Unten is on its prongs the arm will face the **front** of the tank. Put the horn screw through the gear's centre bore into the spline.
4. 6705ZZ into **arm_base_upper**, then lower it over the gear's hub into arm_base_lower (DBI steps 37-40).
5. Arm cables later go down beside the base and into the hull through the 10 mm lid hole next to it.

---

## 7. Build the arm joints (shoulder, elbow, wrist)

Follow DBI's steps 1-27 with these changes. Each joint is the same:

1. Press a **6705ZZ** into each bearing seat: one in the cup with the 3 pins, one in the next link's servo end.
2. **No planets.** Slide **arm_ring** straight onto the 3 pins (its 3 holes go over them).
3. Servo into its pocket from the cover side: shaft up toward the joint, gear on top. M2 screw through the far tab into the link.
4. **arm_joint_gear** onto the cut horn stub, horn screw through the centre.
5. With the servo at 90, hold the joint at its **home angle** while the gears go together:
   - **shoulder:** link tilted 30° forward of straight up
   - **elbow:** bent 70°
   - **wrist:** bent 80° (claw ends up pointing down)
6. Join the two links, then slip an **E-clip** into the groove on the shaft end (DBI step 7). Try sizes from the assortment until one snaps in snug.
7. Cover on (2x M3). The servo's bottom shows through the cover window, which is normal.
8. Thread each servo lead (with an extension) down the cable channels as DBI shows.
9. **Unten** screws onto the base gear's prongs with 2x M3 (DBI step 41).

**Check:** with power on and the controller paired, right stick Y moves the shoulder, L1/R1 the elbow, D-pad up/down the wrist.
If one moves the wrong way, open `arm_tank.ino` and flip that joint's sign in the `GEAR` line (e.g. `-RATIO` → `RATIO`), re-upload. "+" should mean up/back.

---

## 8. Build the claw

1. Claw servo (MG90S) into Gelenk Oben's front end, shaft toward the tip (DBI steps 28-29).
2. **arm_grip_gear** onto the cut horn stub.
3. **arm_grip_pinion** (Stirnrad) loosely into its seat (DBI step 30).
4. **arm_grip_cover** on with 2 screws (DBI step 31).
5. **Jaws last:** hold **L2** until the claw servo stops (its fully-closed end), then slide both **arm_jaw** in from the sides so their fingertips just touch (DBI step 32).
6. **Check:** R2 opens the claw to about 37 mm, L2 closes it.

---

## 9. Camera mast

1. **mast_base** to the lid's rear-left corner: 2x M3x10, nuts under the lid.
2. **mast** into the base on an M3x16 pivot with a nut, snug enough that it doesn't flop.
3. Lock pin: press the printed **knob** onto an M3x16's head; push it through the base's lower hole to lock the mast upright.
4. Pan servo into the mast's top block, shaft up. **pan_yoke** on its horn (servo at 90) with the yoke arm pointing toward the hull centre.
5. Tilt servo into the yoke. **cam_head** on the tilt horn. XIAO drops into the head from the top, lens to the front window.
6. Camera antenna's SMA bulkhead into the ledge behind the mast tube; pigtail to the XIAO. Antenna points straight up.
7. USB-C cable from the screw-terminal adapter up through the mast to the XIAO. Leave a 3-4 cm loop at the hinge.

**Check:** phone on `armtank-cam` → `http://192.168.4.1` shows video; D-pad left/right pans, Square/Cross tilts.

---

## 10. Lid on and final checks

1. Lid on (4 corner screws).
2. Fenders on (3x M3 each side).
3. Final checks:
   - **Y** sends everything home: the claw ends up ~11 cm ahead of the base and ~6.5 cm off the floor.
   - On your phone, the camera can see the claw at home.
   - **Fold test:** press **B** (camera turns to look right), pull the knob pin, fold the mast forward, and pin it in the rear hole. It should lie flat beside the arm. Unfold, pin it, and press **Y**.
   - Turn the base fully both ways (±80°) and check nothing rubs.

---

## 11. Controls

| PS5 input | Does |
|---|---|
| Left stick | drive |
| Right stick X / Y | base turn / shoulder |
| L1 / R1 | elbow |
| D-pad up / down | wrist |
| L2 / R2 | claw close / open |
| Triangle | arm + camera home |
| Circle | fold pose (before folding the mast) |
| D-pad left / right | camera pan |
| Square / Cross | camera tilt up / down |
| R3 (click right stick) | camera recenter |

---

## 12. Troubleshooting

| Problem | Fix |
|---|---|
| Controller won't pair | Hold Create + PS again. The tank needs the ESP32-**32U** (the ESP32-S3 can't do PS5 Bluetooth). |
| Servos jitter or the ESP32 resets when the arm moves | Check the 1000uF cap is in the PCA9685 V+ terminal and the XL4015 reads 5.1 V under load. |
| A joint moves the wrong way | Flip its sign in `GEAR` in `arm_tank.ino`. |
| Shoulder sags with the arm stretched out | The SG90 is the weak joint. Keep the arm bent, loads light, or swap in an MG90S (same pocket). |
| Gears skip | The joint wasn't at its home angle when the gears met: re-do step 7.5 for that joint. |
| No video | Phone must be on `armtank-cam`; open `http://192.168.4.1`; check the camera ribbon is seated on the Sense board. |
| Video choppy at range | Stand the camera antenna straight up; stay within ~20-30 m indoors. |
| Wheels on one side run backwards | Swap that motor pair's two wires at the ZK-5AD. |

**Not done yet:** I have not checked the exact E-clip size (try them from the kit), and the firmware for this version has never been compiled, so watch the first upload for errors.
