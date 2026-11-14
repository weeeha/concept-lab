# Parts

Prices are approximate CAD at the time of writing (2026-11-13), looked up, not guessed. Links go to the vendor page used for the price. "(snippet)" marks a price seen only in a search result.

| Part | Spec that matters | Vendor | Price (CAD) | Link |
|---|---|---|---|---|
| 12 V air pump (SparkFun SFE 12V Air Pump) | 12 V, ~12 W, 1/4" barbs, vacuum rated 0 to 16 inHg; positive-pressure output not on the page, must be bench-tested against the 10 to 30 kPa target (backup: a 12 V pump rated 60 to 70 kPa) | RobotShop.ca | 36.43 | https://ca.robotshop.com/products/sfe-air-pump |
| Air reservoir / regulator + gauge | ~0.5 to 1 L receiver with 1/4" ports, or a small regulator and gauge. Not priced: only 1-gallon automotive tanks (about $134 CAD, snippet) turned up, far oversized | none found | not priced | none |
| Fast 2/2 solenoid valve, 12 V, 1/8" NC (brass, 2 mm orifice) | 8 W coil, direct acting, opens "under one second" per the vendor, which is too slow to confirm for 10 to 20 Hz sputter; test before committing. Listed USD 33.81, converted at an assumed 1 USD = 1.40 CAD | electricsolenoidvalves.com (US) | 47.33 | https://www.electricsolenoidvalves.com/1-8-12v-dc-electric-brass-solenoid-valve-12-volt/ |
| Pressure sensor, Adafruit MPRLS ported breakout | 0 to 25 PSI absolute, I2C 0x18, 24-bit, 2.5 mm port. Listed USD 29.95 (46 in stock), converted at an assumed 1 USD = 1.40 CAD, shipping and duties not included | Adafruit | 41.93 | https://www.adafruit.com/products/3965 |
| Smooth-On Ecoflex 00-30 Trial Unit | Platinum-cure silicone, 1A:1B mix; trial unit size not stated on the page. Listed $32.99 (currency not named, assumed USD), converted at 1.40 | Smooth-On shop | 46.19 | https://shop.smooth-on.com/platinum-cure-silicone-rubber/ecoflex-trade-series |
| Metal-gear servo MG996R x2 (cheek pads), 7.13 each | 11 kg/cm at 6 V, 180 degrees, metal gear. Backordered at time of writing | RobotShop.ca | 14.26 | https://ca.robotshop.com/products/waveshare-mg996r-servo-metal-gear-high-torque |
| Metal-gear micro servo MG90S (drawstring ring) | 1.8 to 2.2 kg/cm, 4.8 to 6 V, 13.4 g. Price from Waveshare via search, currency not confirmed (snippet) | Waveshare | 2.59 (snippet) | https://waveshare.com/MG90S-Servo.htm |
| PCA9685 16-channel servo driver (Waveshare HAT) | 16 ch, 12-bit, I2C, 5 V regulator, up to 3 A | PiShop.ca | 21.95 | https://www.pishop.ca/product/servo-driver-hat-for-raspberry-pi-16-channel-12-bit-i2c |
| 6 V peristaltic pump with silicone tubing (wet mode) | 6 V, flow not listed; backordered at time of writing | RobotShop.ca | 23.49 | https://ca.robotshop.com/products/6v-peristaltic-liquid-pump-with-silicone-tubing |
| Fine mist nozzle (Gardena Micro Mist Nozzle) | Fine garden mist; fitting type not stated and the page says discontinued in some stores (snippet) | Canadian Tire | 8.99 (snippet) | https://www.canadiantire.ca/en/pdp/gardena-micro-mist-nozzle-1990016p.1990016.html |
| Raspberry Pi 5, 4 GB (board only) | In stock; no case, PSU or microSD included | CanaKit (CAD) | 154.95 | https://www.canakit.com/raspberry-pi-5-4gb.html?cid=CAD |
| miniDSP UMIK-1 (v3) USB measurement microphone | Calibrated, omni, USB; 39 left, limit 1 per order | Solen.ca | 142.80 | https://solen.ca/en/products/minidsp-umik-1-minidsp-microphone |
| MOSFET driver board for valve and pump | Generic dual 5 to 36 V, 15 A, PWM trigger module (3.3 V logic ok). Not priced: vendor pages would not show a price | Abra Electronics / others | not priced | https://abra-electronics.com/electromechanical/switches/switch-modules-breakout-boards/mod-mos-a0d514-pwm-mosfet-trigger-switch-driver-module-pwm-regulator-motor-control-board-for-arduino-15a-400w-dc-5v-36v.html |
| 12 V 5 A power supply, UL listed | 12 V, 5 A, on sale from 28.99 | X2 Robotics | 14.99 | https://x2robotics.ca/wall-power-adapters/switching-power-supply-12v-5a-ul-listed |
| Push-fit fittings, 25 pc set for 4/6/8/10/12 mm tube | Includes a 6 mm size (snippet) | Bearings Canada | 35.24 (snippet) | https://bearingscanada.com/products/25pcs-push-to-connect-pneumatic-fittings-set-for-4 |
| Silicone tubing 4/6 mm (4 mm ID, 6 mm OD) | Not priced: no Canadian 4x6 listing found; Bambu Lab CA silicone tube starts at 4.42 for other sizes (snippet) | none found | not priced | https://ca.store.bambulab.com/products/silicone-tube |
| Braided PE (Dyneema-type) line, 50 lb | P-Line Endurx 50 lb, 300 yd spool (far more than needed) (snippet) | Harbour Chandler | 34.93 (snippet) | https://www.harbourchandler.ca/products/p-line-endurx-no-fade-braid-50lb-x-300yd-midnight-black |

**Total, approximate:** $626.07 (sum of the priced rows; excludes the three unpriced rows, shipping, tax and duties; includes 4 snippet-only prices and 3 prices converted from USD)

## Printed parts

| Part | Fits around | Material | Est. print time |
|---|---|---|---|
| Valve housing (the "instrument body") | silicone ring, drawstring guide, air inlet | PETG | ~6 h |
| Ring mould (two-part) | casts the sphincter ring | PLA | ~3 h |
| Cheek pad moulds + servo arms | two silicone pads | PLA / PETG | ~4 h |
| Base and tank cradle | compressor, tank, Pi | PETG | ~5 h |
