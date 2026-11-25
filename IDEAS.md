# Ideas

Things worth building next. Nothing here is in the current firmware.

## Camera tracking for the arm

Goal: point at something in the video, and the tank keeps the camera on it, reaches out and grabs it.
The parts are already on the robot: the XIAO ESP32S3 Sense on the rear-left fender tower sees the scene, and its pan/tilt servos on the PCA9685 know where it's looking.
Build it in stages; each one is useful on its own.

### 1. Camera follows a target (pan/tilt only)
- **What:** the camera locks onto one object and the pan/tilt keeps it centred while you drive.
- **How:** start with the easiest target to see, a bright **colour blob** (a neon ball, tape on the object). Threshold in HSV on a small frame (QQVGA 160x120), take the blob's centroid, and run a P controller: `pan += k * (cx - 80)`, `tilt += k * (cy - 60)`.
- **Better target:** **ArUco / AprilTag** markers. They give you an ID and the target's distance (from the tag size) and don't care about lighting. Print a few 3 cm tags and stick them on the things you want to grab.
- **Where it runs:**
  - (a) **On the phone, recommended.** The page at `http://192.168.4.1` is plain HTML; add JS that draws the MJPEG frames into a `<canvas>` and runs the blob or tag detection there (`js-aruco2` for tags, or TensorFlow.js COCO-SSD to track "cup", "bottle", "sports ball"). The XIAO keeps doing nothing but streaming, and a phone is roughly 50x faster.
  - (b) **On the XIAO itself.** Use `esp-who` / ESP-DL colour detection, or a small model exported from Edge Impulse. It works with no phone, but expect ~5-10 fps.
- **Cost:** $0.

### 2. Get tracking results to the tank's ESP32
- The servos hang off the tank's ESP32, not the XIAO, so the target position has to get across.
- **No wires: ESP-NOW.** The XIAO sends `{cx, cy, size, id}` about 20 times a second to the tank ESP32's MAC. ESP-NOW and Bluepad32's Bluetooth can run at the same time on the ESP32, but it adds latency, so test it.
- **Phone path:** the phone page POSTs to the XIAO (`/target?x=..&y=..`), and the XIAO forwards it over ESP-NOW.
- **Fallback:** a 3-wire UART (TX/RX/GND) with Dupont jumpers between the XIAO and ESP32 header pins. Still no soldering, since both boards have headers, but it's one more cable from the camera tower to the hull.

### 3. Turn "where the camera looks" into "where the arm reaches"
- **Known values:** the camera tower pose is fixed in CAD (`CAM_AT`, `PAN_TAB`, `TILT_Z` in `source/tank.py`). With the target centred, the pan and tilt angles give a ray. Intersect that ray with the floor (z = object height) to get the target's x, y on the ground.
- **Base yaw:** `atan2(y, x - shoulder_x)`.
- **2-link IK in the arm's plane:** the upper arm is 80 mm and the forearm 62 mm joint to joint, plus the 50 mm wrist link and the gripper (`L1`, `L2`, `LW` in `source/tank.py`). Keep the gripper pointing straight down, so the three joint angles add up to 180° from vertical. The poses in `source/build.py` are a ready-made forward-kinematics check. The firmware stores each servo angle in `pos[]`, so IK can write angles straight into it.
- **Ranges:** check the joint ranges before you move (the `LO`/`HI` table in the firmware). If the target is out of reach, drive toward it until it's in range. That's a "creep forward" loop on the drive motors.
- **Calibration:** put a tag at 3 known spots on the floor and fit the pan/tilt-to-position mapping. Servo zeroes and printed parts are never where the CAD says.

### 4. Final approach and grab
- **Gripper tag:** stick a small tag on the gripper housing. With both the target tag and the gripper tag in view, move the arm to close the gap in the image (visual servoing). That fixes the IK error from stage 3.
- **Width:** open the jaws to fit (`width ≈ tag distance * object width in pixels`), lower, then close until the servo current rises. A $2 INA219 on the servo rail would sense that; it's an I2C breakout with headers, so no solder.
- **Lift test:** lift and check the tag moved with the gripper. If it didn't, the grab missed, so retry.

### 5. Nice extras once 1-4 work
- **Tap to grab:** tap an object on the phone video and the tank grabs it (stages 1-4 driven by the tap).
- **Follow-me mode:** wear a tag and the tank follows at 1 m using pan error for steering and tag size for distance.
- **Record and replay arm moves** as a list of servo poses saved in ESP32 flash.

## Other ideas
- **Joint feedback:** add 10k pots on each arm joint (a printed coupling to the joint) read by an ADS1115 (I2C, headers). The firmware then knows the real joint angle even if a horn slips.
- **Soft start:** ramp servos from their last known pose at boot instead of snapping to 90.
- **Battery gauge:** a voltage-divider breakout to an ESP32 ADC pin, with a low-battery rumble on the gamepad.