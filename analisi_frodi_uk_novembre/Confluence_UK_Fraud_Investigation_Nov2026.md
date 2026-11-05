# UK eCommerce Fraud & Bulk Reseller Investigation – Oct/Nov 2026 (`DeLonghi_UK`)

| Document Metadata | Details |
| :--- | :--- |
| **Date of Analysis** | 4 November 2026 |
| **Market / Account** | United Kingdom (`DeLonghi_UK` – SFCC) |
| **Investigated Period** | 1 October 2026 – 4 November 2026 (10,228 GBP transactions screened) |
| **Trigger Event** | Warehouse & Finance alert on bulk FACM coffee machine orders (`£1,274.95` = 5 × `£254.99`) |
| **Total Ring Exposure** | **54 Transactions** (**53 Approved = £64,152.29 / 253 units**; 1 Refused = £1,274.95) |
| **Additional S63 9BL Cluster** | **8 Transactions** in Oct 2026 (**7 Approved = £6,926.18**; 1 Refused = £611.98) |
| **Status** | **Orders on Hold / Pending Cancellation & Refund to Original Payment Method** |
| **Owner / Author** | Elia Ziroldo (Global eCommerce Product Owner) |

---

## 1. Executive Summary

Following an alert from the UK warehouse (Howard Tenens) and UK Finance (Duncan Nicholls) regarding nearly 40 suspicious orders of **£1,274.95** (5 × FACM machines at £254.99 each, totaling ~£50k) placed over 2–3 November 2026, a full forensic audit was conducted across all **10,228 UK transactions** recorded in Adyen between **1 October and 4 November 2026**.

### Key Findings
1. **Why initial Adyen `Shopper DNA` / `Device Fingerprint` lookups only showed 21 orders:**
   - Searching from a single order (`SFDLUK00119344`) linked only **5 orders** via `Shopper Reference` (`abkrIZwHs3lbsRlrwZxqYYk0lF`) and **21 orders** via `Device Fingerprint` (`b8a2f66de0dea849e98b63d42caf577d`), all paid via Visa or PayPal.
   - By screening the entire UK ledger via **Gmail dot-trick canonicalization, timestamp interleaving, card BINs, and delivery warehouse postcodes**, we uncovered that this is a **coordinated 3-identity operation** acting simultaneously within **6 to 10 seconds of each other**.
2. **Complete Scope Uncovered (54 Transactions across 2 Waves):**
   - **Wave 2 (Night of 2–3 Nov 2026, 23:01–01:59 CET):** **44 approved orders** (of which **41 are for £1,274.95**) totaling **£52,677.74 (208 units)** — matching the ~40 orders / ~£50k flagged by UK Finance, including the **11 American Express** transactions.
   - **Wave 1 (24 Oct 2026, 18:12–18:34 CET):** **10 orders** of £1,274.95 (**9 approved = £11,474.55 / 45 units**; 1 Refused) placed by the exact same actors 10 days earlier.
   - **Grand Total (3-Actor Ring):** **53 approved orders** totaling **£64,152.29 (253 units)**.

---

## 2. The 3 Linked Actors & Evasion Techniques (Modus Operandi)

The group used four deliberate evasion tactics to bypass velocity rules, order limits, and Adyen `Shopper DNA` linking:
- **Tactic A — Virtual Card Cycling (Allica Bank BIN `474559`):** Generating a brand-new virtual business card for almost every order (16+ distinct card last-4 digits under the same Allica Bank account).
- **Tactic B — Gmail "Dot Trick" Canonicalization Bypass:** Inserting dots at different positions in the same Gmail address on every checkout (e.g., `j.os.i.ah0000d@gmail.com`, `jos.ia.h00.00d@gmail.com`, `t.hpdistributions@gmail.com`, `th.pdistributions@gmail.com`, `w.e.l.l.sharvi.e@gmail.com`). Gmail routes all variations to the same inbox, while SFCC and Adyen treat each string as a brand-new guest shopper.
- **Tactic C — Intentional Name & Address Typos:** Altering the shopper name (`Josiah Auton`, `Jossiah Auton`, `Josiahh Auton`, `Jos Autn Faulkner`, `Thomas Harry`, `Tahomas Harry`, `Tbhomas Harry`, `Tcom Harry`) and street spelling (`uniit 4b precicisson prep`, `precisioon prep`) on every order to defeat exact-match duplicate filters.
- **Tactic D — Third-Party Amazon FBA Prep Centers:** Shipping bulk stock directly to commercial 3PL FBA prep warehouses (`Precision Prep` at `CV9 1JE` Atherstone, and `Unit 3E Goldthorpe Industrial Estate` at `S63 9BL` Rotherham).

### Actor Breakdown & Cross-Links

| Actor / Identity | Associated Company | Delivery / Billing Postcodes | Payment Methods Used | Canonical Gmail Accounts Used (with Dot-Trick Variants) | Proof of Link to the Ring |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Josiah Auton Falkner** | Auton Trading Ltd (Co. `#15648711`) | **`CV9 1JE`** (Unit 4B Carlyon Rd / Racemeadow Rd, Precision Prep, Atherstone) | • Visa (`474559` Allica Bank – 17 virtual cards)<br>• PayPal (5 tx) | • `josiah0000a@gmail.com` (5 variants)<br>• `josiah0000b@gmail.com` (4 variants)<br>• `josiah0000c@gmail.com` (3 variants)<br>• `josiah0000d@gmail.com` (3 variants)<br>• `autontrading@gmail.com` (3 variants)<br>• `contactautontrading@gmail.com` (4 variants)<br>• `josiahautonfalkner@gmail.com` (2 variants) | Primary seed identified by warehouse (`SFDLUK00119344`). 3 orders had `df-timedOut` and were only caught via full ledger scan. |
| **2. Thomas Harry** | THP Distributions | **`S63 9BL`** (Unit 3E Goldthorpe Ind. Estate, Commercial Rd, Rotherham)<br>• `DE56 4AD` (1 tx) | • Visa (`474559`, `482922`, `478481` Allica Bank)<br>• Amex (`379921`, `374279`) | • `tpbuyermain@gmail.com` (7 variants)<br>• `thpdistributions@gmail.com` (7 variants)<br>• `tpharrtinsta570@gmail.com`<br>• `tpharryinsta570@gmail.com`<br>• `tpbuyer765@gmail.com`<br>• `tpharry570@gmail.com` | Placed £1,274.95 orders **6–10 seconds apart** from Josiah on both Oct 24 (`18:12:52` vs `18:13:02`) and Nov 2 (`23:01:48` vs `23:01:58`); same Allica Bank BIN `474559`, same Gmail dot-trick, same name typo pattern. |
| **3. Harvie Wells** | WellsDirect Ltd | **`S63 9BL`** (Unit 3E Goldthorpe Ind. Estate, Rotherham – 1st order)<br>• **`CV10 9LD`** (321 Bucks Hill, Nuneaton – 10 orders) | • Apple Pay - Amex (`379921` card `4008` – 10 tx)<br>• PayPal (1 tx) | • `wellsharvie@gmail.com` (10 dot-trick variants: `wel.lsharvie`, `wellsharv.ie`, `w.e.l.l.sharvi.e`, etc.) | **Smoking Gun:** On his first order on Nov 2 at `23:09:39` (`SFDLUK00119236`), he used **Thomas Harry's exact Rotherham address (`Unit 3E Goldthorpe Ind. Estate, S63 9BL`)**, before switching 3 minutes later to `CV10 9LD` Nuneaton for 10 Amex orders. |

---

## 3. Financial Summary by Wave, Actor & Payment Method

| Wave | Actor / Cluster | Payment Method | Adyen Status | 3DS Auth | Liability Shift | Total Orders | Orders @ £1,274.95 | Est. Units | Total Amount (GBP) |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | ---: |
| **Wave 2 (02–03 Nov 2026)** | **1. Josiah Auton Falkner (`CV9 1JE`)** | Visa (Allica Bank `474559`) | `SettledBulk` | `Y` | `Y` | 14 | 14 | 70 | £17,849.30 |
| **Wave 2 (02–03 Nov 2026)** | **1. Josiah Auton Falkner (`CV9 1JE`)** | PayPal | `SettledExternally` | `n/a` | `n/a` | 4 | 3 | 16 | £4,079.84 |
| **Wave 2 (02–03 Nov 2026)** | **2. Thomas Harry (`S63 9BL`)** | Visa (Allica Bank `474559`) | `SettledBulk` | `Y` | `Y` | 14 | 14 | 70 | £17,849.30 |
| **Wave 2 (02–03 Nov 2026)** | **2. Thomas Harry (`DE56 4AD`)** | American Express (`374279`) | `SentForSettle` | `Y` | `Y` | 1 | 0 | 1 | £79.90 |
| **Wave 2 (02–03 Nov 2026)** | **3. Harvie Wells (`CV10 9LD`)** | Apple Pay - Amex (`379921`) | `SentForSettle` | `Y` | `Y` | 10 | 9 | 46 | £11,544.45 |
| **Wave 2 (02–03 Nov 2026)** | **3. Harvie Wells (`S63 9BL`)** | PayPal | `SettledExternally` | `n/a` | `n/a` | 1 | 1 | 5 | £1,274.95 |
| **Subtotal Wave 2 (Nov 2–3)** | *All 3 Linked Actors* | *All Methods* | *All Approved* | | | **44** | **41** | **208** | **£52,677.74** |
| **Wave 1 (24 Oct 2026)** | **1. Josiah Auton Falkner (`CV9 1JE`)** | Visa (Allica Bank `474559`) | `SettledBulk` | `Y` | `Y` | 5 | 5 | 25 | £6,374.75 |
| **Wave 1 (24 Oct 2026)** | **1. Josiah Auton Falkner (`CV9 1JE`)** | PayPal | `SettledExternally` | `n/a` | `n/a` | 1 | 1 | 5 | £1,274.95 |
| **Wave 1 (24 Oct 2026)** | **2. Thomas Harry (`S63 9BL`)** | Apple Pay - Amex (`379921`) | `Settled` | `Y` | `Y` | 1 | 1 | 5 | £1,274.95 |
| **Wave 1 (24 Oct 2026)** | **2. Thomas Harry (`S63 9BL`)** | Apple Pay - Visa (`482922`) | `SettledBulk` | `Y` | `Y` | 2 | 2 | 10 | £2,549.90 |
| **Wave 1 (24 Oct 2026)** | **2. Thomas Harry (`S63 9BL`)** | Apple Pay - Visa (`478481`) | `Refused` | `Y` | `Y` | *(1)* | *(1)* | *(5)* | *(£1,274.95)* |
| **Subtotal Wave 1 (Oct 24)** | *Approved Only (excl. 1 Refused)* | *All Methods* | *Approved* | | | **9** | **9** | **45** | **£11,474.55** |
| **GRAND TOTAL (Approved)** | **All 3 Linked Actors** | **All Methods** | **Approved** | | | **53** | **50** | **253** | **£64,152.29** |

---

## 4. Risk Assessment & Action Plan

### 4.1 Why Liability Shift Does Not Eliminate Risk Here
1. **PayPal Orders (6 orders / £6,629.74):** `Liability Indicator = n/a`. PayPal Seller Protection explicitly excludes deliveries made to third-party freight forwarders / prep centers (`Precision Prep` and `Goldthorpe Industrial Estate`) and orders where the recipient name/address is altered.
2. **American Express Orders (12 orders / £12,899.30):** Although Apple Pay tokenisation provides `3D Authenticated = Y`, Amex chargebacks under *Goods Not Received / Commercial Disputes* when delivered to a multi-tenant 3PL prep warehouse carry a very low win rate for the merchant. Note that **11 of the 12 Amex orders are currently in `SentForSettle` status**.
3. **Allica Bank Visa Business Cards (35 approved orders / £44,623.25):** 3DS Liability Shift (`Y`) protects against *10.4 Fraud - Card Absent*, but **does not protect** against *13.1 Merchandise Not Received* (friendly fraud / corporate bust-out fraud) at a 3PL warehouse, and violates B2C eCommerce Terms of Sale (commercial bulk purchasing above household limits).

### 4.2 Immediate Operational Actions
- [x] **Action 1 — Warehouse Hold (Logistics / Howard Tenens):** Hold all **44 orders from Wave 2 (Nov 2–3)** across `CV9 1JE` (Atherstone), `S63 9BL` (Rotherham), and `CV10 9LD` (Nuneaton). Verify dispatch/delivery status of the **9 approved orders from Wave 1 (Oct 24)**.
- [ ] **Action 2 — Order Cancellation & Adyen Refunds:** Cancel all held orders in SFCC/SAP and issue refunds **strictly back to the original payment method / PSP Reference in Adyen**.
- [ ] **Action 3 — Adyen RevenueProtect Velocity Rules Configuration:**
  1. **Device Fingerprint / Persistent Cookie Velocity Rule:** Block if `> 3 transactions` within `24 hours` share the same `Device Fingerprint` or `Persistent Cookie`.
  2. **Delivery / Billing Postcode Velocity Rule:** Block/Review if `> 3 transactions` within `48 hours` target the same UK postcode (e.g., `CV9 1JE`, `S63 9BL`, `CV10 9LD`).
  3. **Account Holder Name / Card BIN Velocity Rule:** Block if `> 3 transactions` within `24 hours` share the same `Account Holder Name` (`Josiah Auton Falkner`, `Thomas Harry`, `Harvie Wells`).

---

## 5. Complete Transaction Lists

### 5.1 Wave 2 — Night of 2–3 November 2026 (44 Orders – £52,677.74)

| # | Creation Date (CET) | Merchant Reference | PSP Reference | Actor | Payment Method | Card BIN / Last4 | Value (GBP) | Est. Units | Status | 3DS / Liab. | Shopper Name | Shopper Email (Raw) | Canonical Email | Postcode | Device Fingerprint |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- | ---: | :-: | :--- | :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | `2026-11-02 01:23:54` | **`SFDLUK00119005`** | `DG7ZG6XJ3GS9WKR9` | 2. Thomas Harry | American Express | `374279 / 3005` | **£79.90** | 1 | `SentForSettle` | `Y` / `Y` | Thomas Harry | `tpharrtinsta570@gmail.com` | `tpharrtinsta570@gmail.com` | `DE564AD` | `48c911fb592a480311e3612c6d58acbd` |
| 2 | `2026-11-02 23:01:48` | **`SFDLUK00119307`** | `MM426NH66L67CSZ3` | 1. Josiah Auton Falkner | Visa | `474559 / 7338` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Auton | `jos.iah.00.00.a@gmail.com` | `josiah0000a@gmail.com` | `CV91JE` | `df-timedOut` |
| 3 | `2026-11-02 23:01:58` | **`SFDLUK00119306`** | `HSNV3X65RCKDX2F3` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `tpharrtinsta570@gmail.com` | `tpharrtinsta570@gmail.com` | `S639BL` | `df-timedOut` |
| 4 | `2026-11-02 23:05:08` | **`SFDLUK00119308`** | `QGVW2JRX46343BG3` | 1. Josiah Auton Falkner | Visa | `474559 / 1513` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Auton Falkner | `jos.iah.000.0.a@gmail.com` | `josiah0000a@gmail.com` | `CV91JE` | `df-timedOut` |
| 5 | `2026-11-02 23:05:14` | **`SFDLUK00119309`** | `MNB22JRX46343BG3` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `t.pbuyermain@gmail.com` | `tpbuyermain@gmail.com` | `S639BL` | `None` |
| 6 | `2026-11-02 23:07:24` | **`SFDLUK00119238`** | `ZG542LLCSC39GXG6` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `tp.buyermain@gmail.com` | `tpbuyermain@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 7 | `2026-11-02 23:07:43` | **`SFDLUK00119237`** | `GVD3X275RCKDX2F3` | 1. Josiah Auton Falkner | Visa | `474559 / 2761` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Jos Autn Faulkner | `josiah.0000.b@gmail.com` | `josiah0000b@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 8 | `2026-11-02 23:09:36` | **`SFDLUK00119239`** | `QC5XSFCRXJXS7TG6` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `tpb.uyermain@gmail.com` | `tpbuyermain@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 9 | `2026-11-02 23:09:39` | **`SFDLUK00119236`** | `RVMV8R2KXX5J9FG3` | 3. Harvie Wells | PayPal | `PayPal` | **£1,274.95** | 5 | `SettledExternally` | `-` / `-` | Harvie Wells | `wellsharvie@gmail.com` | `wellsharvie@gmail.com` | `S639BL` | `cfe7b5fe123a488639ff805264d6c14d` |
| 10 | `2026-11-02 23:09:54` | **`SFDLUK00119240`** | `GVPRPPLDN3PX9VW3` | 1. Josiah Auton Falkner | Visa | `474559 / 8710` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josieh Autons | `josiah.00.00.b@gmail.com` | `josiah0000b@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 11 | `2026-11-02 23:11:27` | **`SFDLUK00119311`** | `RGQMRRM5825NWRG6` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `tpbu.yermain@gmail.com` | `tpbuyermain@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 12 | `2026-11-02 23:13:04` | **`SFDLUK00119312`** | `P7FBPSCRXXHM4724` | 3. Harvie Wells | Apple Pay - American Express | `379921 / 4008` | **£1,274.95** | 5 | `SentForSettle` | `Y` / `Y` | Harvie Wells | `wel.lsharvie@gmail.com` | `wellsharvie@gmail.com` | `CV109LD` | `cfe7b5fe123a488639ff805264d6c14d` |
| 13 | `2026-11-02 23:16:30` | **`SFDLUK00119241`** | `M7MMKR36RTGLB8H3` | 3. Harvie Wells | Apple Pay - American Express | `379921 / 4008` | **£1,274.95** | 5 | `SentForSettle` | `Y` / `Y` | Harvie Wells | `wellsharv.ie@gmail.com` | `wellsharvie@gmail.com` | `CV109LD` | `cfe7b5fe123a488639ff805264d6c14d` |
| 14 | `2026-11-02 23:30:12` | **`SFDLUK00119315`** | `VLXQHVKFBG686PP9` | 3. Harvie Wells | Apple Pay - American Express | `379921 / 4008` | **£1,274.95** | 5 | `SentForSettle` | `Y` / `Y` | Harvie Wells | `wellsha.rvie@gmail.com` | `wellsharvie@gmail.com` | `CV109LD` | `cfe7b5fe123a488639ff805264d6c14d` |
| 15 | `2026-11-02 23:35:09` | **`SFDLUK00119242`** | `VCHTQX35XNPF3KQ9` | 3. Harvie Wells | Apple Pay - American Express | `379921 / 4008` | **£1,274.95** | 5 | `SentForSettle` | `Y` / `Y` | Harvie Wells | `wellsharvi.e@gmail.com` | `wellsharvie@gmail.com` | `CV109LD` | `cfe7b5fe123a488639ff805264d6c14d` |
| 16 | `2026-11-02 23:46:06` | **`SFDLUK00119316`** | `JFFHNSTVPJNBVXG6` | 3. Harvie Wells | Apple Pay - American Express | `379921 / 4008` | **£1,274.95** | 5 | `SentForSettle` | `Y` / `Y` | Harvie Wells | `w.ells.har.vie@gmail.com` | `wellsharvie@gmail.com` | `CV109LD` | `cfe7b5fe123a488639ff805264d6c14d` |
| 17 | `2026-11-02 23:48:52` | **`SFDLUK00119244`** | `PXRWGTH58XNSJPZ3` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `tpbuyer.main@gmail.com` | `tpbuyermain@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 18 | `2026-11-02 23:49:13` | **`SFDLUK00119245`** | `GJQ4P9SX46343BG3` | 3. Harvie Wells | Apple Pay - American Express | `379921 / 4008` | **£1,274.95** | 5 | `SentForSettle` | `Y` / `Y` | Harvie Wells | `w.e.l.l.sharvi.e@gmail.com` | `wellsharvie@gmail.com` | `CV109LD` | `cfe7b5fe123a488639ff805264d6c14d` |
| 19 | `2026-11-02 23:50:53` | **`SFDLUK00119246`** | `G3P66GX9MBVK3NR9` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `tpbuyerm.ain@gmail.com` | `tpbuyermain@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 20 | `2026-11-02 23:52:59` | **`SFDLUK00119247`** | `TDVX6HX9MBVK3NR9` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `t.hpdistributions@gmail.com` | `thpdistributions@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 21 | `2026-11-02 23:55:01` | **`SFDLUK00119320`** | `TKTPHXH58XNSJPZ3` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `th.pdistributions@gmail.com` | `thpdistributions@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 22 | `2026-11-02 23:56:59` | **`SFDLUK00119321`** | `MQRBNZBP49Z3MMG6` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `thp.distributions@gmail.com` | `thpdistributions@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 23 | `2026-11-03 00:00:14` | **`SFDLUK00119322`** | `QMXR7LMDN3PX9VW3` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `thpd.istributions@gmail.com` | `thpdistributions@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 24 | `2026-11-03 00:02:10` | **`SFDLUK00119323`** | `ZX9VX92G9JFLFJP9` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `thpdi.stributions@gmail.com` | `thpdistributions@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 25 | `2026-11-03 00:04:43` | **`SFDLUK00119249`** | `VJJXGJ4BVM6RPVX3` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `thpdis.tributions@gmail.com` | `thpdistributions@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 26 | `2026-11-03 00:07:28` | **`SFDLUK00119324`** | `M53J3GDRXJXS7TG6` | 2. Thomas Harry | Visa | `474559 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Thomas Harry | `thpdist.ributions@gmail.com` | `thpdistributions@gmail.com` | `S639BL` | `48c911fb592a480311e3612c6d58acbd` |
| 27 | `2026-11-03 00:09:50` | **`SFDLUK00119251`** | `Q3TR88VVPJNBVXG6` | 3. Harvie Wells | Apple Pay - American Express | `379921 / 4008` | **£1,274.95** | 5 | `SentForSettle` | `Y` / `Y` | Harvie Wells | `we.ll.sha.r.vie@gmail.com` | `wellsharvie@gmail.com` | `CV109LD` | `cfe7b5fe123a488639ff805264d6c14d` |
| 28 | `2026-11-03 00:12:48` | **`SFDLUK00119326`** | `ZPP6LJQWBWZS3NQ9` | 3. Harvie Wells | Apple Pay - American Express | `379921 / 4008` | **£1,274.95** | 5 | `SentForSettle` | `Y` / `Y` | Harvie Wells | `w.ell.sha.r.v.ie@gmail.com` | `wellsharvie@gmail.com` | `CV109LD` | `cfe7b5fe123a488639ff805264d6c14d` |
| 29 | `2026-11-03 00:26:24` | **`SFDLUK00119252`** | `DTLPLRNV7GDRVLD3` | 3. Harvie Wells | Apple Pay - American Express | `379921 / 4008` | **£1,274.95** | 5 | `SentForSettle` | `Y` / `Y` | Harvie Wells | `w.el.ls.har.vie@gmail.com` | `wellsharvie@gmail.com` | `CV109LD` | `cfe7b5fe123a488639ff805264d6c14d` |
| 30 | `2026-11-03 00:27:50` | **`SFDLUK00119253`** | `KW3ZTVG73SXZKFX3` | 1. Josiah Auton Falkner | Visa | `474559 / 7942` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Auton Faulkner | `josi.ah000.0c@gmail.com` | `josiah0000c@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 31 | `2026-11-03 00:35:12` | **`SFDLUK00119254`** | `WB5BJR6X9Z87CHQ9` | 3. Harvie Wells | Apple Pay - American Express | `379921 / 4008` | **£69.90** | 1 | `SentForSettle` | `Y` / `Y` | Harvie Wells | `wellsharvie@gmail.com` | `wellsharvie@gmail.com` | `CV109LD` | `cfe7b5fe123a488639ff805264d6c14d` |
| 32 | `2026-11-03 00:40:27` | **`SFDLUK00119328`** | `F2645RVVPJNBVXG6` | 1. Josiah Auton Falkner | Visa | `474559 / 0128` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiahh Autons | `con.tactauto.ntrading@gmail.com` | `contactautontrading@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 33 | `2026-11-03 00:42:59` | **`SFDLUK00119255`** | `PNC2JDFRXXHM4724` | 1. Josiah Auton Falkner | Visa | `474559 / 0341` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Autonn | `j.osiah.0000a@gmail.com` | `josiah0000a@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 34 | `2026-11-03 00:45:53` | **`SFDLUK00119329`** | `ZG9TLV7Q2T2M2NZ3` | 1. Josiah Auton Falkner | Visa | `474559 / 3198` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Jossiah Auton | `cont.act.autontr.ading@gmail.com` | `contactautontrading@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 35 | `2026-11-03 01:21:21` | **`SFDLUK00119331`** | `VZ4VL3RM739P99G6` | 1. Josiah Auton Falkner | Visa | `474559 / 9025` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Auton | `j.osiah.00.00.b@gmail.com` | `josiah0000b@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 36 | `2026-11-03 01:28:24` | **`SFDLUK00119337`** | `M7ZMPTPV7GDRVLD3` | 1. Josiah Auton Falkner | Visa | `474559 / 3076` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah A Falkner | `auton.tr.ading@gmail.com` | `autontrading@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 37 | `2026-11-03 01:30:36` | **`SFDLUK00119338`** | `GJXPFQ7X9Z87CHQ9` | 1. Josiah Auton Falkner | Visa | `474559 / 5797` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiahh Aut Falkner | `josiah0.0.00d@gmail.com` | `josiah0000d@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 38 | `2026-11-03 01:32:27` | **`SFDLUK00119257`** | `FZ52VDQNTT9R2GR9` | 1. Josiah Auton Falkner | Visa | `474559 / 0756` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Hauton | `j.os.i.ah0000d@gmail.com` | `josiah0000d@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 39 | `2026-11-03 01:34:29` | **`SFDLUK00119339`** | `MR8D2BRM739P99G6` | 1. Josiah Auton Falkner | Visa | `474559 / 1103` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Falkner | `jo.si.ah.0.000c@gmail.com` | `josiah0000c@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 40 | `2026-11-03 01:36:57` | **`SFDLUK00119340`** | `HQXDH9PDN3PX9VW3` | 1. Josiah Auton Falkner | Visa | `474559 / 7392` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiahh Auton | `jos.ia.h00.00d@gmail.com` | `josiah0000d@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 41 | `2026-11-03 01:49:31` | **`SFDLUK00119344`** | `HQGD475PM4FGWBF3` | 1. Josiah Auton Falkner | PayPal | `PayPal` | **£1,274.95** | 5 | `SettledExternally` | `-` / `-` | Josiah Auton | `con.tac.tautont.rading@gmail.com` | `contactautontrading@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 42 | `2026-11-03 01:53:34` | **`SFDLUK00119359`** | `SKLQJNN65NG93RX3` | 1. Josiah Auton Falkner | PayPal | `PayPal` | **£1,274.95** | 5 | `SettledExternally` | `-` / `-` | Josiah Auton | `jos.iah.00.0.0a@gmail.com` | `josiah0000a@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 43 | `2026-11-03 01:56:31` | **`SFDLUK00119360`** | `PPPNBMLQ2FG4P6H6` | 1. Josiah Auton Falkner | PayPal | `PayPal` | **£1,274.95** | 5 | `SettledExternally` | `-` / `-` | Jossiah Auton | `j.osiah.000.0.a@gmail.com` | `josiah0000a@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 44 | `2026-11-03 01:59:43` | **`SFDLUK00119346`** | `VJJBW72JZVXKWSD3` | 1. Josiah Auton Falkner | PayPal | `PayPal` | **£254.99** | 1 | `SettledExternally` | `-` / `-` | josiah Auton | `josi.ah0.00.0c@gmail.com` | `josiah0000c@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |

---

### 5.2 Wave 1 — 24 October 2026 (10 Orders: 9 Approved = £11,474.55 + 1 Refused)

| # | Creation Date (CET) | Merchant Reference | PSP Reference | Actor | Payment Method | Card BIN / Last4 | Value (GBP) | Est. Units | Status | 3DS / Liab. | Shopper Name | Shopper Email (Raw) | Canonical Email | Postcode | Device Fingerprint |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- | ---: | :-: | :--- | :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | `2026-10-24 18:12:52` | **`SFDLUK00116960`** | `NR592K7LPX8T7GZ3` | 2. Thomas Harry | Apple Pay - American Express | `379921 / 3005` | **£1,274.95** | 5 | `Settled` | `Y` / `Y` | Thomas Harry | `tpbuyermain@gmail.com` | `tpbuyermain@gmail.com` | `S639BL` | `329158023032842bf46c4f95315790a1` |
| 2 | `2026-10-24 18:13:02` | **`SFDLUK00116958`** | `X2GFPTM684MVHNQ9` | 1. Josiah Auton Falkner | PayPal | `PayPal` | **£1,274.95** | 5 | `SettledExternally` | `-` / `-` | Josiah Auton Falkner | `contactautontrading@gmail.com` | `contactautontrading@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 3 | `2026-10-24 18:14:56` | **`SFDLUK00116962`** | `SPT6B95GN7LBSPP9` | 2. Thomas Harry | Apple Pay - Visa | `482922 / 2649` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Tahomas Harry | `tpbuyer765@gmail.com` | `tpbuyer765@gmail.com` | `S639BL` | `329158023032842bf46c4f95315790a1` |
| 4 | `2026-10-24 18:16:37` | **`SFDLUK00116964`** | `VR373CRJH3S3X6Q9` | 2. Thomas Harry | Apple Pay - Visa | `482922 / 3827` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Tbhomas Harry | `tpharry570@gmail.com` | `tpharry570@gmail.com` | `S639BL` | `329158023032842bf46c4f95315790a1` |
| 5 | `2026-10-24 18:17:49` | **`SFDLUK00116917`** | `XWFNXW2CRSDZTZF3` | 1. Josiah Auton Falkner | Visa | `474559 / 4774` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Falkner | `autontrading@gmail.com` | `autontrading@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 6 | `2026-10-24 18:19:19` | **`SFDLUK00116965`** | `LXL7L2JS9VLWD5H6` | 2. Thomas Harry | Apple Pay - Visa | `478481 / 3455` | **£1,274.95** | 5 | `Refused` | `Y` / `Y` | Tcom Harry | `tpharryinsta570@gmail.com` | `tpharryinsta570@gmail.com` | `S639BL` | `329158023032842bf46c4f95315790a1` |
| 7 | `2026-10-24 18:26:47` | **`SFDLUK00116919`** | `RHJTMH985BC9T2R9` | 1. Josiah Auton Falkner | Visa | `474559 / 4774` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Auton Falkner | `auton.trading@gmail.com` | `autontrading@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 8 | `2026-10-24 18:28:51` | **`SFDLUK00116920`** | `V5QVRJ985BC9T2R9` | 1. Josiah Auton Falkner | Visa | `474559 / 8716` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Auton Falkner | `josiahautonfalkner@gmail.com` | `josiahautonfalkner@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 9 | `2026-10-24 18:30:49` | **`SFDLUK00116969`** | `JF7MM8ZTTS6G54R9` | 1. Josiah Auton Falkner | Visa | `474559 / 9432` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Auton Falkner | `josiah0000b@gmail.com` | `josiah0000b@gmail.com` | `CV91JE` | `b8a2f66de0dea849e98b63d42caf577d` |
| 10 | `2026-10-24 18:34:17` | **`SFDLUK00116970`** | `H8898WZML8F3XVG6` | 1. Josiah Auton Falkner | Visa | `474559 / 3146` | **£1,274.95** | 5 | `SettledBulk` | `Y` / `Y` | Josiah Auton | `josiahaut.onfalkner@gmail.com` | `josiahautonfalkner@gmail.com` | `CV91JE` | `df-timedOut` |

---

### 5.3 Additional Historical Orders at `S63 9BL` (Unit 3E Goldthorpe Ind. Estate, Rotherham – Oct 2026)

During the full postcode audit of `S63 9BL` (`Unit 3E Goldthorpe Industrial Estate, Commercial Road, Rotherham`), an earlier cluster of **7 American Express orders** placed on **7 October 2026 (19:55–21:04 CET)** under the surname **Brewin** (`Jack Brewin`, `Jamie Brewin`, `Joel Brewin`, `Lee Brewin`) and 1 PayPal order on **29 October 2026** (`Adil Akhtar Maison FourNine`) were also identified at the exact same unit:

| # | Creation Date (CET) | Merchant Reference | PSP Reference | Actor | Payment Method | Card BIN / Last4 | Value (GBP) | Est. Units | Status | 3DS / Liab. | Shopper Name | Shopper Email (Raw) | Canonical Email | Postcode | Device Fingerprint |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- | ---: | :-: | :--- | :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | `2026-10-07 19:55:18` | **`SFDLUK00111776`** | `LVS9BJ73PG8HHVZ3` | 4. Other S63 9BL Rotherham | American Express | `340251 / 2004` | **£917.97** | - | `Settled` | `Y` / `Y` | Jack Brewin | `jackbrewin1@gmail.com` | `jackbrewin1@gmail.com` | `S639BL` | `df-timedOut` |
| 2 | `2026-10-07 20:21:28` | **`SFDLUK00111866`** | `TKZ3F22QV2FVJ8G3` | 4. Other S63 9BL Rotherham | American Express | `340252 / 1005` | **£917.97** | - | `Settled` | `Y` / `Y` | Jamie Brewin | `jamiebru19@icloud.com` | `jamiebru19@icloud.com` | `S639BL` | `85eb4c171d98efed6571cbbe5b1a55d6` |
| 3 | `2026-10-07 20:28:08` | **`SFDLUK00111870`** | `DHWKQV3K8CXMS6G3` | 4. Other S63 9BL Rotherham | American Express | `376469 / 6009` | **£917.97** | - | `Settled` | `Y` / `Y` | Joel Brewin | `joelbrewin15@gmail.com` | `joelbrewin15@gmail.com` | `S639BL` | `85eb4c171d98efed6571cbbe5b1a55d6` |
| 4 | `2026-10-07 20:34:18` | **`SFDLUK00111872`** | `V8Z456P29BTBWSF3` | 4. Other S63 9BL Rotherham | American Express | `376469 / 6009` | **£917.97** | - | `Settled` | `Y` / `Y` | Joel Brewin | `joelbru7@gmail.com` | `joelbru7@gmail.com` | `S639BL` | `df-timedOut` |
| 5 | `2026-10-07 20:49:05` | **`SFDLUK00111791`** | `T5DWVNC82HXB93R9` | 4. Other S63 9BL Rotherham | American Express | `376469 / 6009` | **£1,529.95** | - | `Settled` | `Y` / `Y` | Joel Brewin | `annabel.scarfe24@gmail.com` | `annabelscarfe24@gmail.com` | `S639BL` | `None` |
| 6 | `2026-10-07 20:58:59` | **`SFDLUK00111884`** | `K48LHT7LMM2236H6` | 4. Other S63 9BL Rotherham | American Express | `376469 / 6009` | **£1,529.95** | - | `Settled` | `Y` / `Y` | Joel Brewin | `jeanette.scarfe@googlemail.com` | `jeanettescarfe@googlemail.com` | `S639BL` | `85eb4c171d98efed6571cbbe5b1a55d6` |
| 7 | `2026-10-07 21:04:28` | **`SFDLUK00111799`** | `Q8ZCR3WRQSDZTZF3` | 4. Other S63 9BL Rotherham | American Express | `376469 / 6009` | **£611.98** | - | `Refused` | `Y` / `Y` | Joel Brewin | `dscarfe19@gmail.com` | `dscarfe19@gmail.com` | `S639BL` | `85eb4c171d98efed6571cbbe5b1a55d6` |
| 8 | `2026-10-29 22:44:04` | **`SFDLUK00118365`** | `KWFCCHPGT6WL3WF3` | 4. Other S63 9BL Rotherham | PayPal | `PayPal` | **£194.40** | - | `SettledExternally` | `-` / `-` | Adil Akhtar Maison FourNine | `mypurchasingonline2@outlook.com` | `mypurchasingonline2@outlook.com` | `S639BL` | `df-timedOut` |
