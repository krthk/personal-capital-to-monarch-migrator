# Test Data for PC to Monarch Migration Script

This directory contains test data files used for validating the Personal Capital to Monarch Money conversion script.

## Directory Structure

- `input/` - Personal Capital CSV files for testing
- `expected_output/` - Expected Monarch Money CSV output files

## Test Files Description

### Input Files

1. **sample_format2.csv**
   - Tests standard Personal Capital format (Date, Description, Category, Tags, Amount)
   - Contains real transaction types: gas stations, parking, transfers, credit card payments
   - Tests category mappings: "Gasoline/Fuel" → "Gas", "Parking" → "Parking & Tolls", etc.

2. **edge_case_special_chars.csv**
   - Tests handling of special characters in descriptions
   - Includes: commas, quotes, ampersands, accented characters
   - Validates CSV escaping and encoding

3. **edge_case_zero_amounts.csv**
   - Tests transactions with zero or very small amounts
   - Includes: $0.00 transactions, $0.01 amounts, negative small amounts
   - Validates decimal precision handling

4. **sample_with_tags.csv**
   - Tests preservation of tags from Personal Capital
   - Contains various tag formats: single tags, comma-separated tags
   - Validates tag field mapping

5. **empty_file.csv**
   - Tests handling of empty CSV files (headers only, no data)
   - Edge case for error handling

### Expected Output Files

Each input file has a corresponding `-monarch.csv` expected output file that demonstrates:
- Correct 8-column Monarch format
- Proper field mapping (Description → Merchant, etc.)
- Category remapping using the CATEGORY_MAPPINGS dictionary
- Empty Account field (for manual assignment in Monarch)
- Preserved amount signs (negative for expenses, positive for income)
- Tag preservation

## Category Mappings Tested

These test files validate the following category mappings:
- "Gasoline/Fuel" → "Gas"
- "Parking" → "Parking & Tolls"
- "Transfers" → "Transfer"
- "Credit Card Payments" → "Credit Card Payment"
- "Travel" → "Travel & Vacation"
- "Child" → "Kids Gear & Supplies"
- "Entertainment" → "Entertainment & Recreation"
- "Investment Income" → "Dividends & Capital Gains"
- "Service Charges/Fees" → "Service Charges"
- "Paychecks/Salary" → "Paychecks"
- "ATM/Cash" → "Cash & ATM"

## Usage in Tests

These files are used by the test suite to:
1. Test individual function behavior (unit tests)
2. Validate end-to-end file conversion (integration tests)
3. Verify edge case handling
4. Ensure no data loss or corruption during conversion
5. Validate Monarch format compliance