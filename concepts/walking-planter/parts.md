# Parts

Prices are CAD before tax and shipping, checked 2026-11-07. "Fetched" means the vendor page was
read; "snippet" means a search result only, to re-check before ordering.

| Part | Spec that matters | Vendor | Price (CAD) | Link |
|---|---|---|---|---|
| Waveshare HexArth | ESP32, 18 bus servos 12 V, IMU, INA219, 12.6 V charger included. US$439.99, no CAD listing found | Waveshare | ~607 (US$439.99 converted) | https://www.waveshare.com/hexarth.htm |
| 6 × Molicel P28A 18650 | 2800 mAh, 35 A (12.5C), flat top, for the 3s2p holder. Snippet | Rotor Village | ~72.00 (3 × 23.99) | https://rotorvillage.ca/molicel-p28a-18650-2800mah-35a-li-ion-2pc/ |
| Raspberry Pi 5 2GB | Host on the top plate over UART. Fetched, in stock | PiShop.ca | 110.50 | https://www.pishop.ca/product/raspberry-pi-5-2gb/ |
| Ambient light sensor | DFRobot 0-200 klx, I2C, under the clear dome | RobotShop CA | 12.71 | https://ca.robotshop.com/products/dfrobot-ambient-light-sensor-0-200klx |
| Capacitive soil moisture v2 | Analog | X2 Robotics | 4.19 | https://x2robotics.ca/sensors/capacitive-soil-moisture-sensor-module-v2-0 |
| ADS1115 ADC | Pi has no analog input; for the moisture probe | (not priced yet) | | |
| 12 cm plastic pot | IKEA NYPON fits a 12 cm grower pot; the NYPON itself weighs 0.24 kg, so plant straight into a thin grower pot instead | IKEA Canada | 3.99 | https://www.ikea.com/ca/en/p/nypon-plant-pot-indoor-outdoor-gray-40395617/ |
| LECA clay pebbles | Light mix with a little soil; use part of the bag. Snippet | The Seed Company | 13.99 | https://theseedcompany.ca/products/airplant-copy |
| PETG 1 kg | Carapace, dome ring, dock pad | Filaments.ca | 15.99 | https://filaments.ca/products/econofil-standard-petg-white |
| Dock spring contacts | Two pogo/spring contacts wired to the 5.5×2.1 charge jack | (not priced yet) | | |

**Total, approximate:** $840 CAD, about $607 of it the HexArth.

## Notes

- **Cells:** the HexArth wants 10C+. Samsung 30Q (3000 mAh) is only 5C; Molicel P28A (2800 mAh,
  35 A) clears it. The P42A people recommend is a 21700 and does not fit the 18650 holder.
- **Weight:** the planted pot gets ~650 g of the 1 kg walking payload. A 12 cm thin grower pot
  with LECA and a small pothos lands around 450 to 550 g; a decorative pot on top does not fit.

## Printed parts

| Part | Fits around | Material | Est. print time |
|---|---|---|---|
| Carapace with pot cradle | HexArth top plate (152 × 136 mm), Pi 5, cell pack | PETG, ribbed thin wall | ~10 h |
| Light-sensor dome ring | DFRobot sensor board, clear cap bought or printed clear | PETG | ~1 h |
| Dock pad | belly contacts, 300 × 300 mm footprint | PETG | ~6 h |
