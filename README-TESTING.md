# Test Suite for Personal Capital to Monarch Migration Script

This document describes the comprehensive test suite for the PC to Monarch migration script, designed to ensure robust functionality as you extend and modify the codebase.

## Overview

The test suite provides **93% code coverage** with **35 comprehensive tests** covering:
- Unit tests for individual functions
- Integration tests for end-to-end workflows
- Edge case testing with real transaction data
- Error handling and data integrity validation

## Test Structure

### Core Test Files

1. **`test_migrate_pc_to_monarch.py`** - Main test suite (30 tests)
   - Unit tests for all core functions
   - Data transformation validation
   - Category mapping verification
   - File I/O testing

2. **`test_main_integration.py`** - Integration tests (5 tests)
   - End-to-end workflow testing
   - Directory management validation
   - Error handling scenarios

3. **`test_data/`** - Real transaction data for testing
   - Sample input files with various edge cases
   - Expected output files for validation
   - Comprehensive documentation of test scenarios

## Running Tests

### Basic Test Execution
```bash
# Run all tests
python -m pytest test_migrate_pc_to_monarch.py test_main_integration.py -v

# Run with coverage report
python -m pytest test_migrate_pc_to_monarch.py test_main_integration.py --cov=migrate_pc_to_monarch --cov-report=term-missing

# Run specific test class
python -m pytest test_migrate_pc_to_monarch.py::TestCategoryMappings -v
```

### Coverage Analysis
```bash
# Generate HTML coverage report
python -m pytest --cov=migrate_pc_to_monarch --cov-report=html
# View report: open htmlcov/index.html

# Generate detailed coverage report
python -m pytest --cov=migrate_pc_to_monarch --cov-report=term-missing
```

## Test Categories

### 1. Category Mapping Tests (`TestCategoryMappings`)
- ✅ `test_get_category_mappings_returns_dict` - Validates mapping function returns proper dictionary
- ✅ `test_category_mappings_content` - Tests specific real category mappings from your data
- ✅ `test_category_mappings_no_duplicates` - Ensures mapping keys are unique

**Real mappings tested:**
- "Gasoline/Fuel" → "Gas"
- "Parking" → "Parking & Tolls" 
- "Credit Card Payments" → "Credit Card Payment"
- "Child" → "Kids Gear & Supplies"
- And 15+ more from your actual transaction data

### 2. Format Detection Tests (`TestFormatDetection`)
- ✅ `test_detect_format2_standard` - Standard PC format detection
- ✅ `test_detect_format1_investment` - Investment format with Action/Quantity/Price
- ✅ `test_detect_format2_missing_investment_columns` - Handles partial investment columns
- ✅ `test_detect_format_empty_headers` - Graceful handling of malformed headers

### 3. Transaction Transformation Tests (`TestTransactionTransformation`)
- ✅ `test_transform_basic_transaction` - Core field mapping validation
- ✅ `test_transform_unmapped_category` - Handling of unknown categories
- ✅ `test_transform_with_action_field` - Investment format processing
- ✅ `test_transform_missing_fields` - Graceful handling of incomplete data
- ✅ `test_transform_special_characters` - Unicode and special character preservation

### 4. File I/O Tests (`TestFileReading`, `TestFileWriting`)
- ✅ CSV reading with encoding validation
- ✅ Empty file handling
- ✅ Error handling for missing files
- ✅ Monarch format compliance validation
- ✅ Header structure verification

### 5. End-to-End Conversion Tests (`TestEndToEndConversion`)
**Uses your real transaction data:**
- ✅ `test_convert_sample_format2` - Full conversion with 10 real transactions
- ✅ `test_convert_special_characters` - McDonald's, Café Délicieux, quoted strings
- ✅ `test_convert_with_tags` - Tag preservation ("organic,weekly", "business,trip")
- ✅ `test_convert_zero_amounts` - $0.00, $0.01, -$0.50 handling
- ✅ `test_convert_empty_file` - Empty CSV processing

### 6. Data Integrity Tests (`TestDataIntegrity`)
- ✅ `test_amount_sign_preservation` - Negative expenses, positive income
- ✅ `test_monarch_format_compliance` - Exact 8-column structure
- ✅ `test_no_data_loss` - Complete data preservation validation

### 7. Error Handling Tests (`TestErrorHandling`)
- ✅ `test_malformed_csv_handling` - Graceful degradation
- ✅ `test_unicode_handling` - International character support

### 8. Main Function Integration Tests (`TestMainIntegration`)
- ✅ `test_main_with_no_input_directory` - Missing input directory
- ✅ `test_main_with_empty_input_directory` - Empty input folder
- ✅ `test_main_with_test_data` - Complete workflow with real data
- ✅ `test_main_error_handling` - Error recovery and reporting
- ✅ `test_main_output_directory_creation_error` - Directory creation issues

## Real Data Testing

The test suite uses **real transaction data** from your Personal Capital exports:

### Sample Transactions Tested
```csv
2024-08-01,"Payment - Thank You","Transfers",,104.93
2024-07-14,"Sq *boardwalk - Parking Santa Cruz Ca","Parking",,-60
2024-06-27,"Grand Gas Union San Jose Ca","Gasoline/Fuel",,-48.92
2023-11-27,"The Home Depot","Child",,-3.01
```

### Expected Monarch Output
```csv
2024-08-01,Payment - Thank You,Transfer,,Payment - Thank You,,104.93,
2024-07-14,Sq *boardwalk - Parking Santa Cruz Ca,Parking & Tolls,,Sq *boardwalk - Parking Santa Cruz Ca,,-60,
2024-06-27,Grand Gas Union San Jose Ca,Gas,,Grand Gas Union San Jose Ca,,-48.92,
2023-11-27,The Home Depot,Kids Gear & Supplies,,The Home Depot,,-3.01,
```

## Test Development Guidelines

### Adding New Tests
1. **Real Data First**: Use actual transaction data from your exports
2. **Edge Cases**: Test boundary conditions and error scenarios  
3. **Configuration Ready**: Design tests to easily adapt when configuration files are added
4. **Mock Strategically**: Mock external dependencies, not core logic

### Test Naming Convention
```python
def test_[function_name]_[scenario]_[expected_result]():
    """Clear description of what is being tested and why."""
```

### Test Data Management
- Use `test_data/input/` for sample Personal Capital files
- Use `test_data/expected_output/` for expected Monarch conversions
- Document all test scenarios in `test_data/README.md`

## Continuous Integration Ready

The test suite is designed for CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pip install -r requirements-dev.txt
    python -m pytest --cov=migrate_pc_to_monarch --cov-report=xml
    
- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage.xml
```

## Performance Benchmarks

- **Test Execution Time**: ~0.07 seconds for full suite
- **Memory Usage**: Minimal (temp files cleaned up)
- **Coverage**: 93% (missing only error handling edge cases)

## Configuration File Preparation

The test suite is designed to easily accommodate the upcoming configuration file feature:

1. **`get_category_mappings()`** function is already extracted and easily mockable
2. **Parameterized tests** can switch between hardcoded and config-based mappings
3. **Configuration validation tests** can be added without restructuring

## Future Enhancements

Potential test improvements:
1. **Performance testing** with large transaction files (1000+ transactions)
2. **Fuzz testing** with randomly generated transaction data
3. **Property-based testing** using hypothesis library
4. **Integration with Monarch's actual import validation**

## Troubleshooting

### Common Issues
1. **Test data missing**: Ensure `test_data/` directory exists
2. **Coverage too low**: Add tests for error handling paths
3. **Tests fail on different OS**: Use `pathlib.Path` for cross-platform compatibility

### Debug Mode
```bash
# Run with detailed output
python -m pytest -v -s --tb=long

# Run single test with debugging
python -m pytest test_migrate_pc_to_monarch.py::TestCategoryMappings::test_category_mappings_content -v -s
```

This comprehensive test suite ensures your migration script is robust, reliable, and ready for future enhancements!