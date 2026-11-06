# Parts (concept)

Prices are CAD before tax and shipping, pulled 2026-11-06. "Fetched" means the vendor page was
read; "snippet" means a search result only, to re-check before ordering.

| Part | Spec that matters | Vendor | Price (CAD) | Link |
|---|---|---|---|---|
| Chassis (prototype) | Dagu Multi-Chassis 4WD Basic: aluminum, 4x 48:1 gearmotors, 65 mm wheels. Fetched, in stock. No stated payload. | RobotShop CA | 49.93 | https://ca.robotshop.com/products/multi-chassis-4wd-robot-kit-basic |
| Chassis (if grass) | Lynxmotion Tri-Track: tracked, 2x 12 V 50:1 motors, ~2.3 kg payload. Fetched, backorder. | RobotShop CA | 516.83 | https://ca.robotshop.com/products/lynxmotion-tri-track-chassis-ttrkcb-kt |
| Raspberry Pi 5, 4 GB | Fetched, in stock. (Pi Zero 2 W is 21.95 but out of stock.) | PiShop.ca | 156.85 | https://www.pishop.ca/product/raspberry-pi-5-4gb/ |
| Motor driver HAT | DFRobot 7-12 V, TB6612FNG, 1.2 A per channel, I2C. Fetched, backorder. | RobotShop CA | 21.29 | https://ca.robotshop.com/products/7-12v-12a-dc-motor-driver-hat-raspberry-pi |
| Battery | Gens Ace 3S 5000 mAh 60C, XT60. Snippet only. | Zone Hobbies | ~102.99 | https://zonehobbies.net/products/gea503s60x6gt-gens-ace-g-tech-11-1v-60c-3s-5000mah-lipo-battery-pack-with-xt60-plug |
| Charger | iMAX B6AC 1-6S balance charger. Fetched, not available; another Canadian RC shop needed. | rcjaz.ca | 97.70 | https://www.rcjaz.ca/imax-new-b6ac-balance-charger-p-90017308.html |
| Qi pair (Pi power only) | Transmitter + receiver, 5 V 1 A out. Fetched, in stock. Cannot charge the 3S pack. | X2 Robotics | 9.79 | https://x2robotics.ca/robot-parts/chargers/wireless-charging-module-5v-1a |
| Soil moisture sensor | Capacitive v2.0, analog. Fetched, in stock. | X2 Robotics | 4.19 | https://x2robotics.ca/sensors/capacitive-soil-moisture-sensor-module-v2-0 |
| Light sensor | DFRobot ambient light, 0-200 klx, I2C. Fetched, backorder. | RobotShop CA | 12.71 | https://ca.robotshop.com/products/dfrobot-ambient-light-sensor-0-200klx |
| Distance sensor | HC-SR04 ultrasonic, 2-400 cm. Fetched, in stock. | X2 Robotics | 1.99 | https://x2robotics.ca/hc-sr04-ultrasonic-ranging-sensor-5v |
| 15 cm pot | Bloem Dayton 6 in with saucer. Snippet only. | Canadian Tire | 3.99 | https://www.canadiantire.ca/en/pdp/bloem-dayton-planter-6-in-1592096p.html |
| PETG, 1 kg | EconoFil Standard PETG White 1.75 mm. Fetched, in stock. | Filaments.ca | 15.99 | https://filaments.ca/products/econofil-standard-petg-white |

**Total, approximate:** $477 with the Dagu chassis; about $944 with the Tri-Track. About $273
of the $477 is from fetched pages; battery, charger and pot are snippet prices.

## Known gaps before ordering

- **Payload.** The Dagu's hobby gearmotors are unlikely to move 2 kg of pot and soil on grass.
  It is a bench prototype; grass means the Tri-Track or a lighter pot.
- **Motor current.** 1.2 A per channel is thin for four motors under load: parallel two
  channels per side, or a second driver board.
- **Dock.** No 12 V Qi receiver found in Canada. Charging the pack means spring contacts on
  the printed ramp, with a 3S balance charger behind them (unpriced).

## Printed parts

| Part | Fits around | Material | Est. print time |
|---|---|---|---|
| Shell ring + cradle | Dagu footprint, 15 cm pot | PETG | ~9 h |
| Sensor mast with rain hood | HC-SR04, light sensor | PETG | ~2 h |
| Dock ramp with contact holders | chassis wheelbase | PETG | ~5 h |
| Battery tray | 3S 5000 mAh pack (~155 x 48 x 40 mm) | PETG | ~2 h |
