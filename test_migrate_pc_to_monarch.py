#!/usr/bin/env python3
"""
Comprehensive Test Suite for Personal Capital to Monarch Migration Script

This test suite validates all aspects of the migration script functionality:
- Unit tests for individual functions
- Integration tests for end-to-end file conversion  
- Edge case testing with real data samples
- Category mapping validation
- Data integrity verification

The tests use real transaction data from the user's Personal Capital exports
to ensure the conversion works correctly with actual data patterns.

Run with: python -m pytest test_migrate_pc_to_monarch.py -v
Coverage: python -m pytest test_migrate_pc_to_monarch.py --cov=migrate_pc_to_monarch --cov-report=html
"""

import pytest
import csv
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch, mock_open

# Import the functions we're testing
from migrate_pc_to_monarch import (
    get_category_mappings,
    detect_pc_format,
    read_pc_transactions,
    transform_transaction,
    track_category_remapping,
    write_monarch_csv,
    convert_pc_to_monarch
)


class TestCategoryMappings:
    """Test category mapping functionality."""
    
    def test_get_category_mappings_returns_dict(self):
        """Test that get_category_mappings returns a dictionary."""
        mappings = get_category_mappings()
        assert isinstance(mappings, dict)
        assert len(mappings) > 0
    
    def test_category_mappings_content(self):
        """Test specific category mappings from user's real data."""
        mappings = get_category_mappings()
        
        # Test mappings that appear in the user's test data
        # Note: With case_sensitive_matching: false, keys are lowercase
        assert mappings["gasoline/fuel"] == "Gas"
        assert mappings["transfers"] == "Transfer"
        assert mappings["credit card payments"] == "Credit Card Payment"
        assert mappings["travel"] == "Travel & Vacation"
        assert mappings["child"] == "Child Care"  # Updated mapping in new config
        assert mappings["entertainment"] == "Entertainment & Recreation"
        assert mappings["investment income"] == "Interest"  # Updated mapping in new config
        assert mappings["service charges/fees"] == "Financial Fees"  # Updated mapping in new config
        assert mappings["paychecks/salary"] == "Paychecks"
        assert mappings["atm/cash"] == "Cash & ATM"
    
    def test_category_mappings_no_duplicates(self):
        """Test that all mapping keys are unique."""
        mappings = get_category_mappings()
        keys = list(mappings.keys())
        assert len(keys) == len(set(keys))


class TestFormatDetection:
    """Test Personal Capital format detection."""
    
    def test_detect_format2_standard(self):
        """Test detection of standard format (format2)."""
        headers = ['Date', 'Description', 'Category', 'Tags', 'Amount']
        result = detect_pc_format(headers)
        assert result == 'format2'
    
    def test_detect_format1_investment(self):
        """Test detection of investment format (format1)."""
        headers = ['Date', 'Description', 'Category', 'Action', 'Quantity', 'Price', 'Amount']
        result = detect_pc_format(headers)
        assert result == 'format1'
    
    def test_detect_format2_missing_investment_columns(self):
        """Test that missing investment columns default to format2."""
        headers = ['Date', 'Description', 'Category', 'Action', 'Amount']  # Missing Quantity, Price
        result = detect_pc_format(headers)
        assert result == 'format2'
    
    def test_detect_format_empty_headers(self):
        """Test format detection with empty headers."""
        headers = []
        result = detect_pc_format(headers)
        assert result == 'format2'  # Default to format2


class TestTransactionTransformation:
    """Test individual transaction transformation logic."""
    
    def test_transform_basic_transaction(self):
        """Test transformation of a basic transaction."""
        pc_row = {
            'Date': '2024-01-15',
            'Description': 'Shell Gas Station',
            'Category': 'Gasoline/Fuel',
            'Tags': 'business,trip',
            'Amount': '-45.00'
        }
        mappings = get_category_mappings()
        
        result = transform_transaction(pc_row, mappings)
        
        assert result['Date'] == '2024-01-15'
        assert result['Merchant'] == 'Shell Gas Station'
        assert result['Category'] == 'Gas'  # Mapped from 'Gasoline/Fuel'
        assert result['Account'] == ''  # Always empty
        assert result['Original Statement'] == 'Shell Gas Station'
        assert result['Notes'] == ''  # No Action field in format2
        assert result['Amount'] == '-45.00'
        assert result['Tags'] == 'business,trip'
    
    def test_transform_unmapped_category(self):
        """Test transformation when category has no mapping."""
        pc_row = {
            'Date': '2024-01-15',
            'Description': 'Custom Store',
            'Category': 'Unmapped Category',
            'Tags': '',
            'Amount': '-25.00'
        }
        mappings = get_category_mappings()
        
        result = transform_transaction(pc_row, mappings)
        
        assert result['Category'] == 'Unmapped Category'  # Unchanged
    
    def test_transform_with_action_field(self):
        """Test transformation with Action field (format1)."""
        pc_row = {
            'Date': '2024-01-15',
            'Description': 'AAPL Stock',
            'Category': 'Stocks',
            'Action': 'Buy',
            'Amount': '-1000.00'
        }
        mappings = get_category_mappings()
        
        result = transform_transaction(pc_row, mappings)
        
        assert result['Category'] == 'Stocks'  # Unmapped since 'Stocks' not in updated config
        assert result['Notes'] == 'Buy'  # Action field mapped to Notes
    
    def test_transform_missing_fields(self):
        """Test transformation with missing optional fields."""
        pc_row = {
            'Date': '2024-01-15',
            'Description': 'Test Transaction',
            'Amount': '-10.00'
            # Missing Category, Tags, Action
        }
        mappings = get_category_mappings()
        
        result = transform_transaction(pc_row, mappings)
        
        assert result['Date'] == '2024-01-15'
        assert result['Merchant'] == 'Test Transaction'
        assert result['Category'] == ''  # Missing category
        assert result['Tags'] == ''  # Missing tags
        assert result['Notes'] == ''  # Missing action
        assert result['Amount'] == '-10.00'
    
    def test_transform_special_characters(self):
        """Test transformation with special characters in description."""
        pc_row = {
            'Date': '2024-01-15',
            'Description': "McDonald's, Inc. & \"Big Store\"",
            'Category': 'Entertainment',
            'Amount': '-12.50'
        }
        mappings = get_category_mappings()
        
        result = transform_transaction(pc_row, mappings)
        
        assert result['Merchant'] == "McDonald's, Inc. & \"Big Store\""
        assert result['Original Statement'] == "McDonald's, Inc. & \"Big Store\""
        assert result['Category'] == 'Entertainment & Recreation'


class TestCategoryRemappingTracking:
    """Test category remapping statistics tracking."""
    
    def test_track_category_remapping_new_mapping(self):
        """Test tracking a new category remapping."""
        remapping_counts = {}
        track_category_remapping('Gasoline/Fuel', 'Gas', remapping_counts)
        
        assert 'Gasoline/Fuel' in remapping_counts
        assert remapping_counts['Gasoline/Fuel']['mapped_to'] == 'Gas'
        assert remapping_counts['Gasoline/Fuel']['count'] == 1
    
    def test_track_category_remapping_existing_mapping(self):
        """Test tracking an existing category remapping."""
        remapping_counts = {
            'Gasoline/Fuel': {'mapped_to': 'Gas', 'count': 2}
        }
        track_category_remapping('Gasoline/Fuel', 'Gas', remapping_counts)
        
        assert remapping_counts['Gasoline/Fuel']['count'] == 3
    
    def test_track_category_remapping_no_change(self):
        """Test that no tracking occurs when category doesn't change."""
        remapping_counts = {}
        track_category_remapping('Groceries', 'Groceries', remapping_counts)
        
        assert len(remapping_counts) == 0


class TestFileReading:
    """Test CSV file reading functionality."""
    
    def test_read_pc_transactions_valid_file(self):
        """Test reading a valid Personal Capital CSV file."""
        test_content = """Date,Description,Category,Tags,Amount
2024-01-15,Shell Gas Station,Gasoline/Fuel,business,-45.00
2024-01-14,Starbucks,Entertainment,coffee,-5.75"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(test_content)
            f.flush()
            
            try:
                transactions, pc_format = read_pc_transactions(f.name)
                
                assert pc_format == 'format2'
                assert len(transactions) == 2
                assert transactions[0]['Description'] == 'Shell Gas Station'
                assert transactions[1]['Description'] == 'Starbucks'
            finally:
                os.unlink(f.name)
    
    def test_read_pc_transactions_empty_file(self):
        """Test reading an empty CSV file."""
        test_content = "Date,Description,Category,Tags,Amount\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(test_content)
            f.flush()
            
            try:
                transactions, pc_format = read_pc_transactions(f.name)
                
                assert pc_format == 'format2'
                assert len(transactions) == 0
            finally:
                os.unlink(f.name)
    
    def test_read_pc_transactions_nonexistent_file(self):
        """Test reading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            read_pc_transactions('nonexistent_file.csv')


class TestFileWriting:
    """Test CSV file writing functionality."""
    
    def test_write_monarch_csv_valid_data(self):
        """Test writing valid transaction data to Monarch CSV."""
        transactions = [
            {
                'Date': '2024-01-15',
                'Merchant': 'Shell Gas Station',
                'Category': 'Gas',
                'Account': '',
                'Original Statement': 'Shell Gas Station',
                'Notes': '',
                'Amount': '-45.00',
                'Tags': 'business'
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            try:
                write_monarch_csv(transactions, f.name)
                
                # Read back and verify
                with open(f.name, 'r') as read_file:
                    reader = csv.DictReader(read_file)
                    rows = list(reader)
                    
                    assert len(rows) == 1
                    assert rows[0]['Merchant'] == 'Shell Gas Station'
                    assert rows[0]['Category'] == 'Gas'
                    assert rows[0]['Amount'] == '-45.00'
            finally:
                os.unlink(f.name)
    
    def test_write_monarch_csv_empty_data(self):
        """Test writing empty transaction data."""
        transactions = []
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            try:
                write_monarch_csv(transactions, f.name)
                
                # Read back and verify headers exist
                with open(f.name, 'r') as read_file:
                    reader = csv.DictReader(read_file)
                    rows = list(reader)
                    
                    assert len(rows) == 0
                    # Check headers are correct
                    expected_headers = ['Date', 'Merchant', 'Category', 'Account', 
                                     'Original Statement', 'Notes', 'Amount', 'Tags']
                    assert reader.fieldnames == expected_headers
            finally:
                os.unlink(f.name)


class TestEndToEndConversion:
    """Test end-to-end file conversion using real test data."""
    
    def test_convert_sample_format2(self):
        """Test conversion of sample format2 file."""
        input_file = 'test_data/input/sample_format2.csv'
        expected_file = 'test_data/expected_output/sample_format2-monarch.csv'
        
        # Skip if test files don't exist
        if not os.path.exists(input_file) or not os.path.exists(expected_file):
            pytest.skip("Test data files not found")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            try:
                transaction_count, remapping_counts = convert_pc_to_monarch(input_file, f.name)
                
                # Verify transaction count
                assert transaction_count == 10  # Based on sample_format2.csv
                
                # Verify some remappings occurred
                assert 'Gasoline/Fuel' in remapping_counts
                assert 'Transfers' in remapping_counts
                assert 'Child' in remapping_counts  # This category should be remapped
                
                # Read generated file and compare with expected
                with open(f.name, 'r') as generated, open(expected_file, 'r') as expected:
                    generated_reader = csv.DictReader(generated)
                    expected_reader = csv.DictReader(expected)
                    
                    generated_rows = list(generated_reader)
                    expected_rows = list(expected_reader)
                    
                    assert len(generated_rows) == len(expected_rows)
                    
                    # Compare first row in detail
                    if generated_rows:
                        assert generated_rows[0]['Date'] == expected_rows[0]['Date']
                        assert generated_rows[0]['Merchant'] == expected_rows[0]['Merchant']
                        assert generated_rows[0]['Category'] == expected_rows[0]['Category']
                        assert generated_rows[0]['Amount'] == expected_rows[0]['Amount']
                        
            finally:
                os.unlink(f.name)
    
    def test_convert_special_characters(self):
        """Test conversion of file with special characters."""
        input_file = 'test_data/input/edge_case_special_chars.csv'
        
        if not os.path.exists(input_file):
            pytest.skip("Test data file not found")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            try:
                transaction_count, remapping_counts = convert_pc_to_monarch(input_file, f.name)
                
                assert transaction_count == 5  # Based on edge_case_special_chars.csv
                
                # Read and verify special characters are preserved
                with open(f.name, 'r', encoding='utf-8') as output_file:
                    reader = csv.DictReader(output_file)
                    rows = list(reader)
                    
                    # Check that special characters are preserved
                    merchants = [row['Merchant'] for row in rows]
                    assert any("McDonald's" in merchant for merchant in merchants)
                    assert any("Café Délicieux" in merchant for merchant in merchants)
                    assert any("Big Box Store" in merchant for merchant in merchants)
                    
            finally:
                os.unlink(f.name)
    
    def test_convert_with_tags(self):
        """Test conversion preserves tags correctly."""
        input_file = 'test_data/input/sample_with_tags.csv'
        
        if not os.path.exists(input_file):
            pytest.skip("Test data file not found")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            try:
                transaction_count, remapping_counts = convert_pc_to_monarch(input_file, f.name)
                
                # Read and verify tags are preserved
                with open(f.name, 'r') as output_file:
                    reader = csv.DictReader(output_file)
                    rows = list(reader)
                    
                    # Find row with tags and verify they're preserved
                    tagged_rows = [row for row in rows if row['Tags']]
                    assert len(tagged_rows) > 0
                    
                    # Check specific tag preservation
                    assert any("organic,weekly" in row['Tags'] for row in tagged_rows)
                    assert any("business,trip" in row['Tags'] for row in tagged_rows)
                    
            finally:
                os.unlink(f.name)
    
    def test_convert_zero_amounts(self):
        """Test conversion handles zero and small amounts correctly."""
        input_file = 'test_data/input/edge_case_zero_amounts.csv'
        
        if not os.path.exists(input_file):
            pytest.skip("Test data file not found")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            try:
                transaction_count, remapping_counts = convert_pc_to_monarch(input_file, f.name)
                
                # Read and verify amounts are preserved exactly
                with open(f.name, 'r') as output_file:
                    reader = csv.DictReader(output_file)
                    rows = list(reader)
                    
                    amounts = [row['Amount'] for row in rows]
                    assert '0.00' in amounts
                    assert '0.01' in amounts
                    assert '-0.50' in amounts
                    
            finally:
                os.unlink(f.name)
    
    def test_convert_empty_file(self):
        """Test conversion of empty CSV file."""
        input_file = 'test_data/input/empty_file.csv'
        
        if not os.path.exists(input_file):
            pytest.skip("Test data file not found")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            try:
                transaction_count, remapping_counts = convert_pc_to_monarch(input_file, f.name)
                
                assert transaction_count == 0
                assert len(remapping_counts) == 0
                
                # Verify file has correct headers
                with open(f.name, 'r') as output_file:
                    reader = csv.DictReader(output_file)
                    expected_headers = ['Date', 'Merchant', 'Category', 'Account', 
                                     'Original Statement', 'Notes', 'Amount', 'Tags']
                    assert reader.fieldnames == expected_headers
                    
            finally:
                os.unlink(f.name)


class TestDataIntegrity:
    """Test data integrity and validation."""
    
    def test_amount_sign_preservation(self):
        """Test that amount signs are preserved correctly."""
        # Negative amount (expense)
        pc_row = {'Date': '2024-01-15', 'Description': 'Store', 'Category': 'Shopping', 'Amount': '-50.00'}
        result = transform_transaction(pc_row, {})
        assert result['Amount'] == '-50.00'
        
        # Positive amount (income)
        pc_row = {'Date': '2024-01-15', 'Description': 'Salary', 'Category': 'Income', 'Amount': '2500.00'}
        result = transform_transaction(pc_row, {})
        assert result['Amount'] == '2500.00'
        
        # Zero amount
        pc_row = {'Date': '2024-01-15', 'Description': 'Free', 'Category': 'Other', 'Amount': '0.00'}
        result = transform_transaction(pc_row, {})
        assert result['Amount'] == '0.00'
    
    def test_monarch_format_compliance(self):
        """Test that output strictly follows Monarch's 8-column format."""
        pc_row = {
            'Date': '2024-01-15',
            'Description': 'Test Store',
            'Category': 'Shopping',
            'Tags': 'test',
            'Amount': '-25.00'
        }
        result = transform_transaction(pc_row, {})
        
        # Verify all 8 required Monarch columns are present
        expected_columns = ['Date', 'Merchant', 'Category', 'Account', 
                          'Original Statement', 'Notes', 'Amount', 'Tags']
        
        assert set(result.keys()) == set(expected_columns)
        
        # Verify Account is empty (for manual assignment in Monarch)
        assert result['Account'] == ''
        
        # Verify Description maps to both Merchant and Original Statement
        assert result['Merchant'] == 'Test Store'
        assert result['Original Statement'] == 'Test Store'
    
    def test_no_data_loss(self):
        """Test that no data is lost during conversion."""
        original_data = {
            'Date': '2024-01-15',
            'Description': 'Complex Store Name & Co., LLC',
            'Category': 'Gasoline/Fuel',
            'Tags': 'business,quarterly,important',
            'Amount': '-123.45'
        }
        
        mappings = get_category_mappings()
        result = transform_transaction(original_data, mappings)
        
        # Verify all original data is preserved or properly mapped
        assert result['Date'] == original_data['Date']
        assert result['Merchant'] == original_data['Description']
        assert result['Original Statement'] == original_data['Description']
        assert result['Tags'] == original_data['Tags']
        assert result['Amount'] == original_data['Amount']
        # Test that category was properly mapped (using same logic as transform_transaction)
        expected_category = mappings.get(original_data['Category']) or mappings.get(original_data['Category'].lower(), original_data['Category'])
        assert result['Category'] == expected_category


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_malformed_csv_handling(self):
        """Test handling of malformed CSV files."""
        # Create a malformed CSV with inconsistent columns
        malformed_content = """Date,Description,Category,Tags,Amount
2024-01-15,Store One,Shopping,tag1,-25.00
2024-01-14,Store Two,Shopping  # Missing amount column"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(malformed_content)
            f.flush()
            
            try:
                # This should not crash, but handle gracefully
                transactions, pc_format = read_pc_transactions(f.name)
                # The CSV reader should still work, just with missing fields
                assert pc_format == 'format2'
                assert len(transactions) >= 1  # At least the valid row
            finally:
                os.unlink(f.name)
    
    def test_unicode_handling(self):
        """Test handling of Unicode characters."""
        pc_row = {
            'Date': '2024-01-15',
            'Description': 'Café München & Résidence',
            'Category': 'Entertainment',
            'Amount': '-15.50'
        }
        
        result = transform_transaction(pc_row, {})
        
        # Unicode characters should be preserved
        assert result['Merchant'] == 'Café München & Résidence'
        assert result['Original Statement'] == 'Café München & Résidence'


if __name__ == '__main__':
    # Run tests when script is executed directly
    pytest.main([__file__, '-v'])