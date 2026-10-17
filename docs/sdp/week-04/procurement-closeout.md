# Week 4 — Module B Procurement Closeout

**Owner:** Ozan — Module B, Embedded Acquisition & Data Path  
**Record date:** 2026-10-18  
**Status:** Public-safe order register based on owner-reported order details; delivery and some line-level reconciliation OPEN.

## 1. Evidence and privacy

Detailed public-safe line ledger: [W04_B_actual-orders_2026-10-16_v01.csv](W04_B_actual-orders_2026-10-16_v01.csv). It preserves the line-level values supplied by the owner and marks VAT rounding, delivery, exact product code and Motorobit add-on reconciliation as open where evidence is missing.

This closeout uses the order details supplied in the project conversation. It intentionally excludes receipts, home address, phone, identity/tax numbers, payment card details and shipping labels. “Ordered / paid (reported)” records the owner's statement, not independent delivery or invoice verification. No delivery date, tracking number or delivery confirmation is claimed unless explicitly provided.

The supplied order summaries mix VAT-inclusive unit prices with VAT-exclusive line subtotals. Use the reported supplier checkout totals as the present cost authority; do not silently recalculate a supplier's gross total from selected line entries.

## 2. Supplier-level purchase register

| Supplier | Date / reference | Reported contents | Reported supplier total | Status / open evidence |
|---|---|---|---:|---|
| Direnc.net | 16.10.2026 per owner; order number not supplied here | 3 × INMP441 I²S mic; 2 × ESP32-S3 N16R8 board; 5 × MCP6022-I/P; 2 × 830-point breadboard; jumper sets, trimpots, headers, DIP-8 sockets, R/C group and 1 m stereo mic cable | 2,343.88 TL | Paid/ordered per owner; delivery not verified. Supplied product subtotal 2,345.88 minus 2.01 discount does not arithmetically equal 2,343.88 (0.01 TL difference). Keep the user-reported final total as authority pending invoice reconciliation. |
| Motorobit | 16.10.2026 per owner; order number not supplied here | 2 × 30 mm / 12 Ω vibration exciter; 4 × PAM8403; 1 × 140-piece jumper kit; 3 × 100K trimpot; 1 × 12×12 cm perfboard; 2 × 1×40 female header | 638.77 TL for the supplied cart, including 137.00 TL shipping | Paid/ordered per owner; delivery not verified. Two 7×9 cm perfboards were reported as added later, but the supplied cart total and the later add-on are not sufficiently reconciled to establish whether the charge is already included. Keep the add-on amount OPEN; do not report a final paid total from the estimated 45 TL/list price. |
| Farnell / SAMM Teknoloji | 16.10.2026; order #FS1228810 | 2 × Kingstate KECG2740PBJ ECM. Product subtotal 168.9674 TL net + shipping 149.0012 TL net + VAT 63.5937 TL | 381.56 TL | Paid by credit card / ordered per owner; delivery not verified. Supplied exact total 381.5624 TL, shown as 381.56 TL. No tracking number or delivery date was supplied. |
| Amazon.com.tr | Order number / exact order date not supplied here | 1 × Juo braided 3.5 mm TRS AUX cable, 1 m | 159.00 TL | Owner-reported ordered; delivery not verified. Shipping 0.00 TL. It is an analog AUX cable, not a USB data cable. |

### Cost control

The four reported supplier totals sum to **3,523.21 TL** (2,343.88 + 638.77 + 381.56 + 159.00). This is a reported subtotal, **not a final audited paid total**, because the Motorobit checkout total has not been reconciled with the two later-added 7×9 cm perfboards. If these were charged separately at an estimated 45.00 TL each, the indicative total would be 3,613.21 TL; that scenario must not be recorded as actual spend without the order confirmation/invoice. Keep tax/rounding reconciliation separate from technical decisions.

## 3. Purchased items and current status

| Project ID | Actual order / quantity | Status | Cost / technical notes |
|---|---|---|---|
| A-02 — ECM | Kingstate KECG2740PBJ ×2 | ORDERED / PAID REPORTED; delivery unverified | One ECM model, two units. Original four-unit target was not fully met; two spare units were not procured. Farnell/SAMM gross total 381.56 TL includes product, freight and VAT. |
| A-03 — digital MEMS | INMP441 I²S breakout ×3 | ORDERED / PAID REPORTED; delivery unverified | Replaces the unpurchased PUI DMM-4026-B-I2S-EB-R candidate for the current prototype. PUI EB-R is NOT purchased. INMP441 datasheet gives 24-bit two's-complement I²S and a typical 60 Hz low-frequency −3 dB point; measure and disclose the actual 20–60 Hz behaviour. |
| A-04 — low-noise op-amp | Microchip MCP6022-I/P DIP-8 ×5 | ORDERED / PAID REPORTED; delivery unverified | For ECM AFE breadboard; bias, gain, filter topology and noise performance remain to be designed and measured. |
| A-05 — passive R/C | R/C group, approximately 140.56 TL | ORDERED / PAID REPORTED; delivery and kit content unverified | This approximate group total is already within Direnc.net's 2,343.88 TL total. Do not add it again. |
| A-06 — MCU | ESP32-S3 N16R8 WiFi Bluetooth board, seller code DSTK22852 ×2 | ORDERED / PAID REPORTED; delivery and PCB revision unverified | Replaces old N8R8 / DevKitC-1 candidate. Seller listing names ESP32-S3-WROOM-1-N16R8; board revision and exact USB-C connector routing still require physical confirmation. |
| A-07 — exciter | Motorobit 30 mm / 12 Ω vibration-resonance speaker ×2 | ORDERED / PAID REPORTED; delivery unverified | Power rating and 20–500 Hz response not verified. Low-level bench test and fixed mechanical coupling are required before any performance claim. |
| A-08 — amplifier | Motorobit PAM8403, 2-channel board ×4 | ORDERED / PAID REPORTED; delivery unverified | Actual quantity is four, not the old two-unit plan. Do not ground a BTL output. Test the real load, distortion and temperature. |
| A-11 — breadboard / jumpers / prototyping | 2 × 830-point breadboard; male-to-male jumper set; 140-piece jumper kit; headers; DIP-8 sockets; 12×12 cm perfboard; two reported 7×9 cm perfboards subject to Motorobit order reconciliation | PARTIALLY ORDERED; kit content and delivery unverified | Lab breadboards/dev boards were reported available before ordering; physically count lab stock and delivered items before buying duplicates. Perfboards are for electronics, not the rigid phantom frame. |
| A-12 — shielded cable / connectors | 1 m stereo microphone cable from Direnc.net; 1 m Juo 3.5 mm TRS AUX cable from Amazon | PARTIALLY ORDERED; exact Direnc SKU/price and delivery OPEN | Direnc order summary states 75.55 TL, but public detail/category listings have displayed different prices. Keep reported order amount pending e-mail/invoice SKU confirmation. AUX cable is A-20 in the working BOM, separate from A-12. No USB data cable is listed in the supplied orders. |

## 4. Group-A 12-category closeout

| # | Mandatory category | Evidence-backed state | Status |
|---:|---|---|---|
| 1 | Acoustic stethoscope donor chestpiece / tubing | No exact donor chestpiece SKU appears in the supplied orders | NOT ORDERED / OPEN — choose SKU and geometry |
| 2 | Electret microphone candidates | 2 × Kingstate KECG2740PBJ procured; alternate Same Sky part was a research reference, not purchased | PARTIAL — one ECM model available when delivered; initial four-unit quantity not met |
| 3 | MEMS microphone candidates (analog and/or I²S) | 3 × INMP441 ordered; PUI EB-R not bought | PARTIAL — current I²S candidate ordered; verify delivery and low-frequency behaviour |
| 4 | Low-noise audio operational amplifier | 5 × MCP6022-I/P | ORDERED — AFE schematic / validation OPEN |
| 5 | Passive component assortment | R/C group about 140.56 TL inside Direnc.net order | ORDERED — physical inventory OPEN |
| 6 | MCU development boards with USB access | 2 × N16R8 boards, DSTK22852 | ORDERED — PCB revision, headers and native USB route OPEN |
| 7 | Small electro-acoustic transducer / exciter | 2 × 30 mm / 12 Ω vibration exciter | ORDERED — response/coupling test OPEN |
| 8 | Small audio amplifier board | 4 × PAM8403 | ORDERED — load/thermal/output test OPEN |
| 9 | Silicone / gel acoustic coupling material | No silicone sheet or gel in supplied order lines | NOT ORDERED |
| 10 | Rigid mechanical phantom frame material | No rigid phantom frame material in supplied order lines | NOT ORDERED |
| 11 | Solderless breadboards and jumper wires | Breadboards, jumpers, headers/sockets and perfboards reported ordered; reusable lab stock also reported available | PARTIAL — count lab/delivered stock before top-up |
| 12 | Shielded audio cables and connectors (3.5 mm / BNC / USB) | Stereo microphone cable and AUX cable reported ordered; no USB data cable shown | PARTIAL — exact mic-cable SKU and appropriate USB DATA cable remain open |

## 5. Laboratory equipment (separate from project costs)

Previously reported available in department / reusable inventory: oscilloscope, function generator, DMM, soldering station, breadboards and development boards. This is an owner availability report, not an independently verified inventory, calibration or performance certificate. Department USB audio interface C-05 was reported unavailable. A personal 3.5 mm-to-USB adapter, if considered for ECM digitization, remains unverified for analog capture, gain/AGC, AC coupling and 20–500 Hz response. Lab-owned equipment is excluded from purchase costs.

## 6. Open procurement actions

- Reconcile Motorobit's original 638.77 TL cart with the later-added two 7×9 cm perfboards using the final order confirmation/invoice. Do not publish the receipt itself if it contains private information.
- Reconcile Direnc.net line VAT display and exact 1 m stereo microphone cable SKU with the order e-mail/invoice; keep the 2,343.88 TL reported checkout total until then.
- At delivery, mark items RECEIVED only after checking exact labels, counts and physical condition. Record tracking/delivery only when available.
- Identify the real N16R8 board revision, pin header map and USB controller routing before choosing the cable or pin assignment.
- Count ordered jumpers, headers, sockets, boards and lab stock before reordering.
- Do not order a PCM1808 module until advisor approval and exact module schematic / supply / clock / input / interface / cost review.
- No physical measurement, delivery completion, or G1 success is claimed by this closeout.
