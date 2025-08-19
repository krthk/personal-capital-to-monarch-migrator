#!/usr/bin/env python3
"""
Personal Capital to Monarch Migration Script

This script converts Personal Capital CSV transaction exports to the format required by Monarch Money.
It processes all CSV files in the 'input' folder and generates converted files with '-monarch' suffix 
in the 'output' folder.

The script handles two different Personal Capital export formats:
1. Format1: Investment accounts with Action, Quantity, Price columns
2. Format2: Standard accounts with Date, Description, Category, Tags, Amount columns

Monarch requires a specific 8-column format:
- Date, Merchant, Category, Account, Original Statement, Notes, Amount, Tags
- Positive amounts = income, negative amounts = expenses
- Account field is left empty for manual assignment in Monarch

Author: Generated for Personal Capital to Monarch migration
Version: 1.0
"""

import csv
import os
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def get_category_mappings() -> Dict[str, str]:
    """
    Get the mapping dictionary from Personal Capital categories to Monarch categories.
    
    This function is extracted to make it easy to replace with configuration file loading
    in the future. Each mapping transforms a Personal Capital category name to the 
    corresponding category name expected by Monarch Money.
    
    Returns:
        Dict[str, str]: Dictionary mapping PC categories to Monarch categories
        
    Examples:
        "Gasoline/Fuel" -> "Gas"
        "Credit Card Payments" -> "Credit Card Payment"
        "Child" -> "Kids Gear & Supplies"
    """
    return {
        # Family and personal care categories
        "Child": "Kids Gear & Supplies",
        "Clothing/Shoes": "Clothing",
        "Healthcare/Medical": "Medical",
        "Pets/Pet Care": "Pets",
        
        # Transportation categories
        "Automotive": "Auto Maintenance",
        "Gasoline/Fuel": "Gas",
        "Parking": "Parking & Tolls",
        
        # Entertainment and lifestyle
        "Travel": "Travel & Vacation",
        "Hobbies": "Poker",  # User-specific mapping
        "Entertainment": "Entertainment & Recreation",
        
        # Financial transactions
        "Credit Card Payments": "Credit Card Payment",
        "Transfers": "Transfer",
        "Service Charges/Fees": "Service Charges",
        "ATM/Cash": "Cash & ATM",
        
        # Income categories
        "Paychecks/Salary": "Paychecks",
        "Dividends Received": "Dividends & Capital Gains",
        "Investment Income": "Dividends & Capital Gains",
        "Stocks": "RSU",  # User-specific: treats stock transactions as RSU
        
        # Housing and utilities
        "Mortgages": "Mortgage",
        "Cable/Satellite": "Internet & Cable",
        "Telephone": "Phone",
        
        # Savings and contributions
        "Retirement Contributions": "Retirement Contribution",
        "529 Contributions": "529 Contribution",
        "Portfolio Management": "Service Charges",
        
        # Other categories
        "Charitable Giving": "Charity",
    }


def detect_pc_format(headers: List[str]) -> str:
    """
    Detect Personal Capital CSV format based on the presence of specific column headers.
    
    Personal Capital exports come in two different formats:
    - Format1: Investment/brokerage accounts that include Action, Quantity, and Price columns
              (used for stock purchases, sales, dividends, etc.)
    - Format2: Standard checking/credit card accounts with basic transaction data
              (Date, Description, Category, Tags, Amount)
    
    Args:
        headers (List[str]): List of column headers from the CSV file
        
    Returns:
        str: 'format1' for investment format with Action/Quantity/Price columns
             'format2' for standard transaction format
             
    Examples:
        ['Date', 'Description', 'Action', 'Quantity', 'Price', 'Amount'] -> 'format1'
        ['Date', 'Description', 'Category', 'Tags', 'Amount'] -> 'format2'
    """
    # Check for the presence of investment-specific columns
    investment_columns = {'Action', 'Quantity', 'Price'}
    header_set = set(headers)
    
    if investment_columns.issubset(header_set):
        return 'format1'
    else:
        return 'format2'


def read_pc_transactions(input_file: str) -> Tuple[List[Dict], str]:
    """
    Read and parse Personal Capital CSV file, detecting the format automatically.
    
    Args:
        input_file (str): Path to the input Personal Capital CSV file
        
    Returns:
        Tuple[List[Dict], str]: (list of transaction dictionaries, detected format)
        
    Raises:
        FileNotFoundError: If the input file doesn't exist
        csv.Error: If the CSV file is malformed
        UnicodeDecodeError: If the file encoding is not UTF-8
    """
    transactions = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            
            # Detect the Personal Capital format based on headers
            pc_format = detect_pc_format(reader.fieldnames or [])
            
            # Read all transactions into memory
            for row in reader:
                transactions.append(row)
                
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {input_file}")
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(f"File encoding error in {input_file}: {e}")
    
    return transactions, pc_format


def transform_transaction(row: Dict[str, str], category_mappings: Dict[str, str]) -> Dict[str, str]:
    """
    Transform a single Personal Capital transaction to Monarch format.
    
    This function handles the core business logic of mapping Personal Capital fields
    to Monarch's required 8-column format. It applies category remapping and ensures
    all required fields are present.
    
    Args:
        row (Dict[str, str]): Single transaction row from Personal Capital CSV
        category_mappings (Dict[str, str]): Category mapping dictionary
        
    Returns:
        Dict[str, str]: Transaction in Monarch format with all 8 required columns
        
    Monarch Format Requirements:
        - Date: Transaction date (preserved from PC)
        - Merchant: Business/entity name (mapped from PC Description)
        - Category: Expense/income category (mapped using category_mappings)
        - Account: Account name (left empty for manual assignment in Monarch)
        - Original Statement: Original transaction description (preserved from PC Description)
        - Notes: Additional notes (mapped from PC Action field if present)
        - Amount: Transaction amount (preserved - negative for expenses, positive for income)
        - Tags: Transaction tags (preserved from PC Tags field if present)
    """
    # Get the original category and apply mapping if it exists
    original_category = row.get('Category', '')
    mapped_category = category_mappings.get(original_category, original_category)
    
    # Build the Monarch transaction record
    # Note: Monarch expects specific column order and naming
    monarch_row = {
        'Date': row.get('Date', ''),
        'Merchant': row.get('Description', ''),  # Business name from transaction description
        'Category': mapped_category,  # Mapped category name
        'Account': '',  # Left empty - user assigns this in Monarch during import
        'Original Statement': row.get('Description', ''),  # Preserve original description
        'Notes': row.get('Action', ''),  # Investment action (Buy/Sell) or empty for standard transactions
        'Amount': row.get('Amount', ''),  # Preserve amount and sign (negative=expense, positive=income)
        'Tags': row.get('Tags', '')  # Preserve any existing tags
    }
    
    return monarch_row


def track_category_remapping(original_category: str, mapped_category: str, remapping_counts: Dict) -> None:
    """
    Track statistics for category remapping to provide user feedback.
    
    Args:
        original_category (str): Original Personal Capital category
        mapped_category (str): Mapped Monarch category
        remapping_counts (Dict): Dictionary to accumulate remapping statistics
    """
    # Only track if a remapping actually occurred
    if mapped_category != original_category:
        if original_category not in remapping_counts:
            remapping_counts[original_category] = {
                'mapped_to': mapped_category, 
                'count': 0
            }
        remapping_counts[original_category]['count'] += 1


def write_monarch_csv(transactions: List[Dict[str, str]], output_file: str) -> None:
    """
    Write transformed transactions to a Monarch-compatible CSV file.
    
    Monarch requires a specific 8-column format in exact order. This function
    ensures the output meets those requirements.
    
    Args:
        transactions (List[Dict[str, str]]): List of transactions in Monarch format
        output_file (str): Path where the output CSV file should be written
        
    Raises:
        IOError: If unable to write to the output file
    """
    # Monarch requires these exact column names in this exact order
    monarch_headers = [
        'Date', 'Merchant', 'Category', 'Account', 
        'Original Statement', 'Notes', 'Amount', 'Tags'
    ]
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=monarch_headers)
            writer.writeheader()
            writer.writerows(transactions)
    except IOError as e:
        raise IOError(f"Unable to write output file {output_file}: {e}")


def convert_pc_to_monarch(input_file: str, output_file: str) -> Tuple[int, Dict]:
    """
    Convert a Personal Capital CSV file to Monarch Money import format.
    
    This is the main conversion function that orchestrates the entire process:
    1. Read and parse the Personal Capital CSV file
    2. Transform each transaction to Monarch format
    3. Track category remapping statistics
    4. Write the output CSV file
    
    Args:
        input_file (str): Path to input Personal Capital CSV file
        output_file (str): Path where Monarch CSV should be written
    
    Returns:
        Tuple[int, Dict]: (number of transactions processed, remapping statistics)
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        IOError: If unable to write output file
        csv.Error: If CSV parsing fails
    """
    # Step 1: Read the Personal Capital transactions
    pc_transactions, pc_format = read_pc_transactions(input_file)
    print(f"Detected {pc_format} for {os.path.basename(input_file)}")
    
    # Step 2: Get category mappings (future: load from config file)
    category_mappings = get_category_mappings()
    
    # Step 3: Transform each transaction and track remapping statistics
    monarch_transactions = []
    remapping_counts = {}
    
    for row in pc_transactions:
        # Transform the transaction to Monarch format
        monarch_row = transform_transaction(row, category_mappings)
        monarch_transactions.append(monarch_row)
        
        # Track category remapping for user feedback
        original_category = row.get('Category', '')
        mapped_category = monarch_row['Category']
        track_category_remapping(original_category, mapped_category, remapping_counts)
    
    # Step 4: Write the Monarch CSV file
    write_monarch_csv(monarch_transactions, output_file)
    
    return len(monarch_transactions), remapping_counts


def main() -> None:
    """
    Main function to process all Personal Capital CSV files in the input folder.
    
    This function orchestrates the entire batch conversion process:
    1. Validates input/output directory structure
    2. Discovers Personal Capital CSV files to convert
    3. Processes each file through the conversion pipeline
    4. Provides detailed progress feedback and statistics
    5. Generates summary report of all conversions and category remappings
    
    Directory Structure Expected:
        input/          - Contains Personal Capital CSV exports
        output/         - Will contain Monarch-compatible CSV files (created if needed)
        
    File Naming Convention:
        Input:  any-filename.csv
        Output: any-filename-monarch.csv
        
    The function skips files that already have '-monarch.csv' suffix to avoid
    re-processing already converted files.
    """
    # Define directory paths
    input_dir = Path('input')
    output_dir = Path('output')
    
    # Step 1: Validate input directory exists
    if not input_dir.exists():
        print("❌ Error: 'input' directory not found!")
        print("Please create an 'input' directory and place your Personal Capital CSV files there.")
        return
    
    # Step 2: Create output directory if it doesn't exist
    try:
        output_dir.mkdir(exist_ok=True)
        print(f"📁 Output directory ready: {output_dir.absolute()}")
    except OSError as e:
        print(f"❌ Error creating output directory: {e}")
        return
    
    # Step 3: Discover Personal Capital CSV files to process
    csv_files = glob.glob(str(input_dir / '*.csv'))
    pc_files = [f for f in csv_files if not f.endswith('-monarch.csv')]
    
    if not pc_files:
        print("⚠️ No Personal Capital CSV files found in 'input' directory!")
        print("Please place your Personal Capital transaction exports (.csv files) in the 'input' folder.")
        return
    
    # Step 4: Process each file and track overall statistics
    print(f"🔍 Found {len(pc_files)} Personal Capital CSV file(s) to convert:")
    
    total_transactions = 0  # Track total transactions across all files
    all_remappings = {}     # Accumulate category remapping statistics
    successful_conversions = 0
    
    for input_file in pc_files:
        # Generate output filename with -monarch suffix in output directory
        input_path = Path(input_file)
        output_filename = input_path.stem + '-monarch.csv'
        output_file = output_dir / output_filename
        
        print(f"\n📄 Processing: {input_path.name}")
        print(f"📤 Output: {output_filename}")
        
        try:
            # Convert the Personal Capital file to Monarch format
            transaction_count, remapping_counts = convert_pc_to_monarch(str(input_file), str(output_file))
            
            # Track success metrics
            total_transactions += transaction_count
            successful_conversions += 1
            print(f"✅ Converted {transaction_count} transactions successfully")
            
            # Accumulate remapping statistics across all files
            # This helps users understand what category changes were made
            for original_category, mapping_info in remapping_counts.items():
                if original_category not in all_remappings:
                    all_remappings[original_category] = {
                        'mapped_to': mapping_info['mapped_to'], 
                        'count': 0
                    }
                all_remappings[original_category]['count'] += mapping_info['count']
            
        except Exception as e:
            # Log errors but continue processing other files
            print(f"❌ Error processing {input_path.name}: {str(e)}")
            print(f"   Skipping this file and continuing with others...")
    
    # Step 5: Display comprehensive summary report
    print(f"\n🎉 Migration complete!")
    print(f"📊 Results Summary:")
    print(f"  • Files processed successfully: {successful_conversions}/{len(pc_files)}")
    print(f"  • Total transactions converted: {total_transactions:,}")
    print(f"  • Output files saved in: {output_dir.absolute()}")
    
    # Display category remapping summary if any occurred
    if all_remappings:
        print(f"\n📋 Category Remapping Summary:")
        print(f"The following Personal Capital categories were automatically mapped to Monarch categories:")
        
        # Sort by count (most frequent first) for better readability
        sorted_remappings = sorted(
            all_remappings.items(), 
            key=lambda x: x[1]['count'], 
            reverse=True
        )
        
        for original_category, mapping_info in sorted_remappings:
            count = mapping_info['count']
            mapped_to = mapping_info['mapped_to']
            print(f"  • {count:,} transactions: '{original_category}' → '{mapped_to}'")
    
    # Step 6: Provide next steps guidance
    print(f"\n📥 Next Steps:")
    print(f"1. Review the converted files in the 'output' directory")
    print(f"2. In Monarch Money, go to each account's details page")
    print(f"3. Use Edit > Upload transactions > Upload a .CSV file")
    print(f"4. Select the corresponding *-monarch.csv file for each account")
    print(f"5. Assign the correct account name during import (Account column is left empty)")
    
    if all_remappings:
        print(f"\n💡 Tip: Review the category remappings above and adjust in Monarch if needed.")


if __name__ == "__main__":
    main()