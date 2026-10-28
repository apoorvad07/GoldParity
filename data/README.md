# GoldParity Market Data Documentation

## Supported Ingestion Formats
GoldParity accepts commodity derivatives trade records in **CSV**, **XLS**, or **XLSX** formats.

### Sample Dataset
- `data/sample_mcx_bhavcopy.csv`: Realistic MCX Bhavcopy snapshot for trade date `15-Oct-2024` featuring all 4 target gold contracts:
  - `GOLDM` (Gold Mini)
  - `GOLDTEN` (Gold 10 Grams)
  - `GOLDGUINEA` (Gold Guinea)
  - `GOLDPETAL` (Gold Petal)
  - `GOLD` (Big Gold benchmark)

### Column Mapping Table

| Canonical Name | Exchange Aliases Supported | Description |
| :--- | :--- | :--- |
| `Symbol` | `SYMBOL`, `COMMODITY`, `CONTRACT`, `INSTRUMENT` | Contract symbol |
| `Date` | `TRADE_DATE`, `TRADEDATE`, `DATE`, `TIMESTAMP` | Trade date (DD-Mon-YYYY, DD-MM-YYYY, YYYY-MM-DD) |
| `ExpiryDate` | `EXPIRY_DT`, `EXPIRY_DATE`, `EXPIRY`, `MATURITY_DATE` | Contract expiry date |
| `Open` | `OPEN_PRICE`, `OPEN`, `OPEN_RATE` | Opening price |
| `High` | `HIGH_PRICE`, `HIGH`, `MAX_PRICE` | Day high price |
| `Low` | `LOW_PRICE`, `LOW`, `MIN_PRICE` | Day low price |
| `Close` | `CLOSE_PRICE`, `CLOSE`, `SETTLEMENT_PRICE`, `LTP` | Settlement or closing price |
| `Volume` | `NO_OF_CONTRACTS`, `VOLUME`, `TRADED_QTY` | Traded volume in contracts/lots |
| `OpenInterest` | `OPEN_INTEREST`, `OI`, `NO_OF_OPEN_CONTRACTS` | Open interest in contracts |

### Strict Date Validation
Date parsing rejects ambiguous US formatted dates (`MM/DD/YYYY`). Explicit supported formats:
- `%d-%b-%Y` (e.g., `15-Oct-2024`, `15-OCT-2024`)
- `%d-%B-%Y` (e.g., `15-October-2024`)
- `%Y-%m-%d` (e.g., `2024-10-15`)
- `%d-%m-%Y` (e.g., `15-10-2024`)
- `%d/%m/%Y` (e.g., `15/10/2024`)
- `%Y/%m/%d` (e.g., `2024/10/15`)
