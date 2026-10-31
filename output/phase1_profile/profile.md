# Phase 1 - Profiling

## Columns
| column_name                     | column_type   |
|:--------------------------------|:--------------|
| row_id                          | BIGINT        |
| Merchant Reference              | VARCHAR       |
| Payment Method                  | VARCHAR       |
| Booking Date                    | TIMESTAMP     |
| TimeZone                        | VARCHAR       |
| Main Currency                   | VARCHAR       |
| Main Amount                     | DECIMAL(18,2) |
| Record Type                     | VARCHAR       |
| Payment Currency                | VARCHAR       |
| Received (PC)                   | DECIMAL(18,2) |
| Authorised (PC)                 | DECIMAL(18,2) |
| Captured (PC)                   | DECIMAL(18,2) |
| Settlement Currency             | VARCHAR       |
| Payable (SC)                    | DECIMAL(18,2) |
| Commission (SC)                 | DECIMAL(18,2) |
| Markup (SC)                     | DECIMAL(18,2) |
| Scheme Fees (SC)                | DECIMAL(18,2) |
| Interchange (SC)                | DECIMAL(18,2) |
| Processing Fee Currency         | VARCHAR       |
| Processing Fee (FC)             | DECIMAL(18,2) |
| Payment Method Variant          | VARCHAR       |
| Issuer Country                  | VARCHAR       |
| Shopper Country                 | VARCHAR       |
| Modification Merchant Reference | VARCHAR       |
| Payable Batch                   | VARCHAR       |
| Unique Terminal ID              | VARCHAR       |
| Store                           | VARCHAR       |
| Modification Psp Reference      | VARCHAR       |
| Issuer Name                     | VARCHAR       |

## Records by Record Type
| Record Type             |   records |   records_eu_ch_uk |
|:------------------------|----------:|-------------------:|
| Received                |    894566 |             768877 |
| Authorised              |    783942 |             677413 |
| SentForSettle           |    773484 |             671511 |
| Settled                 |    584888 |             502074 |
| AuthenticationRequested |    413318 |             372643 |
| SettledExternally       |    189294 |             170450 |
| Refused                 |    104991 |              87343 |
| SentForRefund           |     28135 |              25078 |
| Refunded                |     24268 |              21810 |
| Retried                 |     21950 |              17998 |
| Cancelled               |      9543 |               5232 |
| RefundedExternally      |      4030 |               3446 |
| Error                   |      2924 |               1412 |
| HandledExternally       |      2729 |               2729 |
| Chargeback              |       725 |                304 |
| Expired                 |       477 |                367 |
| RefundFailed            |        89 |                 72 |
| ChargebackReversed      |        73 |                 51 |
| CaptureFailed           |        44 |                 31 |
| SecondChargeback        |        26 |                 24 |
| SettledReversed         |         7 |                  7 |
| RefundedReversed        |         4 |                  4 |
| RefundNotCleared        |         1 |                  1 |

## Date range
| TimeZone   | min_booking_raw     | max_booking_raw     | min_local           | max_local           |   records |   before_start_local |   before_start_raw_eastern |
|:-----------|:--------------------|:--------------------|:--------------------|:--------------------|----------:|---------------------:|---------------------------:|
| EDT        | 2025-03-09 03:01:03 | 2025-11-02 01:54:27 | 2025-03-09 08:01:03 | 2025-11-02 06:54:27 |   2002432 |                    0 |                          0 |
| EST        | 2024-12-31 18:00:47 | 2025-12-31 17:59:59 | 2025-01-01 00:00:47 | 2025-12-31 23:59:59 |   1837076 |                    0 |                        455 |

## Cost columns by Record Type (EU/CH/UK)
| Record Type             |   records |   Commission (SC) n |   Commission (SC) nonzero |   Commission (SC) negative |   Markup (SC) n |   Markup (SC) nonzero |   Markup (SC) negative |   Scheme Fees (SC) n |   Scheme Fees (SC) nonzero |   Scheme Fees (SC) negative |   Interchange (SC) n |   Interchange (SC) nonzero |   Interchange (SC) negative |   Processing Fee (FC) n |   Processing Fee (FC) nonzero |   Processing Fee (FC) negative | settlement_ccys                             | proc_fee_ccys   |
|:------------------------|----------:|--------------------:|--------------------------:|---------------------------:|----------------:|----------------------:|-----------------------:|---------------------:|---------------------------:|----------------------------:|---------------------:|---------------------------:|----------------------------:|------------------------:|------------------------------:|-------------------------------:|:--------------------------------------------|:----------------|
| Received                |    768877 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                  588279 |                        588279 |                              0 | nan                                         | EUR             |
| Authorised              |    677413 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                 3355 |                       3355 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | EUR,PLN,CZK,NOK,CHF,GBP,SEK,RON,DKK,HUF,JPY | nan             |
| SentForSettle           |    671511 |               35008 |                     35008 |                          0 |          321385 |                321367 |                      0 |               321385 |                     319942 |                           0 |               321385 |                     321352 |                           0 |                       0 |                             0 |                              0 | EUR,HUF,CHF,RON,CZK,NOK,GBP,SEK,PLN,DKK     | nan             |
| Settled                 |    502074 |              179941 |                    179941 |                          0 |          322133 |                322115 |                      0 |               322133 |                     320696 |                           0 |               322133 |                     322103 |                           0 |                  358099 |                             0 |                              0 | RON,GBP,NOK,DKK,CHF,CZK,EUR,HUF,SEK,PLN     | nan             |
| AuthenticationRequested |    372643 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | nan                                         | nan             |
| SettledExternally       |    170450 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | nan                                         | nan             |
| Refused                 |     87343 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                40784 |                      40784 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | HUF,PLN,SEK,EUR,GBP,CZK,DKK,JPY,CHF,RON,NOK | nan             |
| SentForRefund           |     25078 |               13906 |                      1172 |                          0 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                   21960 |                         21960 |                              0 | EUR,CZK,DKK,PLN,CHF,NOK,GBP,RON,HUF,SEK     | EUR             |
| Refunded                |     21810 |               21781 |                      8212 |                        698 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                   14196 |                             0 |                              0 | CHF,GBP,DKK,CZK,SEK,RON,EUR,HUF,PLN,NOK     | EUR             |
| Retried                 |     17998 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                14667 |                      14667 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | EUR,DKK,SEK,HUF,GBP,RON,PLN,CHF,JPY,CZK,NOK | nan             |
| Cancelled               |      5232 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                 1518 |                       1518 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | HUF,EUR,GBP,DKK,CZK,RON,SEK,PLN,CHF,NOK     | nan             |
| RefundedExternally      |      3446 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | nan                                         | nan             |
| HandledExternally       |      2729 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | nan                                         | nan             |
| Error                   |      1412 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | nan                                         | nan             |
| Expired                 |       367 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                  176 |                        176 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | EUR,DKK,PLN,CHF,HUF,NOK,CZK,GBP,RON         | nan             |
| Chargeback              |       304 |                 171 |                        18 |                         10 |             119 |                   119 |                      0 |                  119 |                         61 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | CHF,SEK,PLN,NOK,GBP,DKK,HUF,EUR,RON         | nan             |
| RefundFailed            |        72 |                   3 |                         2 |                          2 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                       3 |                             3 |                              3 | CHF,SEK                                     | EUR             |
| ChargebackReversed      |        51 |                   4 |                         4 |                          0 |              42 |                    42 |                      0 |                   42 |                         25 |                          25 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | HUF,DKK,GBP,EUR,RON,NOK,PLN,SEK             | nan             |
| CaptureFailed           |        31 |                   2 |                         2 |                          2 |               3 |                     3 |                      3 |                    3 |                          3 |                           3 |                    3 |                          0 |                           0 |                       0 |                             0 |                              0 | GBP,CHF                                     | nan             |
| SecondChargeback        |        24 |                   0 |                         0 |                          0 |               0 |                     0 |                      0 |                   13 |                         12 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | PLN,GBP,SEK,HUF,EUR,DKK                     | nan             |
| SettledReversed         |         7 |                   7 |                         7 |                          7 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | CZK                                         | nan             |
| RefundedReversed        |         4 |                   4 |                         0 |                          0 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | PLN,GBP                                     | nan             |
| RefundNotCleared        |         1 |                   1 |                         0 |                          0 |               0 |                     0 |                      0 |                    0 |                          0 |                           0 |                    0 |                          0 |                           0 |                       0 |                             0 |                              0 | PLN                                         | nan             |
