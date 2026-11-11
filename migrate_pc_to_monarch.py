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
import argparse
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def load_configuration(config_path: Optional[str] = None) -> Dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path (Optional[str]): Path to configuration file. If None, uses default 'config.yaml'
        
    Returns:
        Dict: Configuration dictionary loaded from YAML file
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If configuration file is malformed
    """
    if config_path is None:
        # Default config.yaml is in the same directory as the script
        config_path = Path(__file__).parent / 'config.yaml'
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please ensure config.yaml exists or specify a custom config file path."
        )
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        if not config:
            raise ValueError("Configuration file is empty")
            
        return config
        
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing configuration file {config_path}: {e}")


def validate_configuration(config: Dict) -> None:
    """
    Validate the structure and content of the configuration dictionary.
    
    Args:
        config (Dict): Configuration dictionary to validate
        
    Raises:
        ValueError: If configuration is invalid or missing required sections
    """
    # Check for required top-level sections
    required_sections = ['category_mappings']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Configuration missing required section: '{section}'")
    
    # Validate category mappings
    category_mappings = config['category_mappings']
    if not isinstance(category_mappings, dict):
        raise ValueError("'category_mappings' must be a dictionary")
    
    if not category_mappings:
        raise ValueError("'category_mappings' cannot be empty")
    
    # Validate that all mappings are strings
    for pc_category, monarch_category in category_mappings.items():
        if not isinstance(pc_category, str) or not isinstance(monarch_category, str):
            raise ValueError(
                f"Category mapping must be string -> string: '{pc_category}' -> '{monarch_category}'")
    
    # Validate settings if present
    if 'settings' in config:
        settings = config['settings']
        if not isinstance(settings, dict):
            raise ValueError("'settings' must be a dictionary")


def get_category_mappings(config_path: Optional[str] = None) -> Dict[str, str]:
    """
    Get the mapping dictionary from Personal Capital categories to Monarch categories.
    
    This function loads category mappings from a YAML configuration file, allowing
    users to customize how Personal Capital categories are mapped to Monarch Money
    categories without modifying the script code.
    
    Args:
        config_path (Optional[str]): Path to custom configuration file. If None, uses 'config.yaml'
        
    Returns:
        Dict[str, str]: Dictionary mapping PC categories to Monarch categories
        
    Examples:
        "Gasoline/Fuel" -> "Gas"
        "Credit Card Payments" -> "Credit Card Payment"  
        "Child" -> "Kids Gear & Supplies"
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If configuration file is invalid
        yaml.YAMLError: If configuration file is malformed
    """
    try:
        # Load and validate configuration
        config = load_configuration(config_path)
        validate_configuration(config)
        
        # Extract category mappings
        category_mappings = config['category_mappings']
        
        # Apply case-insensitive matching if configured
        if config.get('advanced', {}).get('case_sensitive_matching', True) is False:
            # Create case-insensitive mapping by converting keys to lowercase
            case_insensitive_mappings = {}
            for pc_category, monarch_category in category_mappings.items():
                case_insensitive_mappings[pc_category.lower()] = monarch_category
            return case_insensitive_mappings
        
        return category_mappings
        
    except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
        print(f"⚠️ Configuration Error: {e}")
        print(f"🔄 Falling back to default category mappings...")
        
        # Fallback to hardcoded mappings if config file fails
        return get_default_category_mappings()


def get_default_category_mappings() -> Dict[str, str]:
    """
    Get default hardcoded category mappings as fallback.
    
    This function provides the original hardcoded category mappings as a fallback
    when the configuration file cannot be loaded or is invalid.
    
    Returns:
        Dict[str, str]: Dictionary with default PC to Monarch category mappings
    """
    return {
        # Transportation categories  
        "Gasoline/Fuel": "Gas",
        "Automotive": "Auto Maintenance",
        "Parking": "Parking & Tolls",
        
        # Family and personal care
        "Child": "Kids Gear & Supplies",
        "Clothing/Shoes": "Clothing",
        "Healthcare/Medical": "Medical",
        "Pets/Pet Care": "Pets",
        
        # Entertainment and lifestyle
        "Travel": "Travel & Vacation",
        "Entertainment": "Entertainment & Recreation",
        "Hobbies": "Entertainment & Recreation",  # Generic fallback
        
        # Financial transactions
        "Credit Card Payments": "Credit Card Payment",
        "Transfers": "Transfer",
        "Service Charges/Fees": "Service Charges",
        "ATM/Cash": "Cash & ATM",
        
        # Income categories
        "Paychecks/Salary": "Paychecks",
        "Dividends Received": "Dividends & Capital Gains",
        "Investment Income": "Dividends & Capital Gains",
        "Stocks": "Investment",  # Generic fallback
        
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


# Field names transform_transaction() reads out of a parsed row with row.get().
# Export headers are not stable: Empower (formerly Personal Capital) has shipped
# exports whose headers are lower-cased, and a file that has been round-tripped
# through a spreadsheet or a browser download can carry stray padding or a
# UTF-8 BOM on the first header. Because the lookups below are exact, an
# unrecognised header yields an empty Date/Merchant/Amount for every row and the
# script still reports success. Raw headers are therefore folded onto these
# canonical names before rows are transformed.
CANONICAL_FIELDS: Tuple[str, ...] = (
    'Date',
    'Description',
    'Category',
    'Tags',
    'Amount',
    'Action',
    'Quantity',
    'Price',
)

# Monarch's importer silently skips rows that have no date or amount, so a
# missing value here means lost transaction history rather than a visible error.
REQUIRED_FIELDS: Tuple[str, ...] = ('Date', 'Amount')


def canonicalize_headers(fieldnames: List[str]) -> Tuple[Dict[str, str], List[str]]:
    """
    Map raw export headers onto the canonical field names this script reads.

    Matching compares the stripped, lower-cased header against the lower-cased
    canonical name, so 'date', ' Date ' and 'Date' all resolve to 'Date'. When
    two headers would fold onto the same canonical field, only the first one
    claims it; the rest are left as their own names so no column is overwritten.

    Args:
        fieldnames (List[str]): Raw headers from csv.DictReader.fieldnames

    Returns:
        Tuple[Dict[str, str], List[str]]: (raw header -> canonical field,
                                          raw headers that did not fold)

    Examples:
        ['date', 'Description'] -> ({'date': 'Date', 'Description': 'Description'}, [])
    """
    header_map: Dict[str, str] = {}
    unrecognized: List[str] = []
    claimed: set = set()

    for raw_header in fieldnames:
        if raw_header is None:
            continue
        folded = raw_header.strip().lower()
        match = next((field for field in CANONICAL_FIELDS if field.lower() == folded), None)
        if match is not None and match not in claimed:
            header_map[raw_header] = match
            claimed.add(match)
        else:
            header_map[raw_header] = raw_header
            unrecognized.append(raw_header)

    return header_map, unrecognized


def canonicalize_row(row: Dict[str, str], header_map: Dict[str, str]) -> Dict[str, str]:
    """
    Re-key one parsed CSV row onto canonical field names.

    Args:
        row (Dict[str, str]): Parsed row as keyed by csv.DictReader
        header_map (Dict[str, str]): Raw header -> canonical field mapping

    Returns:
        Dict[str, str]: Row keyed by canonical field name plus any extra columns.
        Values in columns that folded onto an already-populated field are kept
        only when they are non-empty and the earlier value was blank.
    """
    canonical_row: Dict[str, str] = {}

    for raw_header, value in row.items():
        if raw_header is None:
            # csv.DictReader parks surplus columns beyond the header row under None.
            continue
        canonical_field = header_map.get(raw_header, raw_header)
        if canonical_field in canonical_row:
            if not str(canonical_row[canonical_field]).strip() and str(value).strip():
                canonical_row[canonical_field] = value
            continue
        canonical_row[canonical_field] = value

    return canonical_row


def validate_monarch_rows(monarch_transactions: List[Dict[str, str]], input_file: str,
                          max_listed: int = 10) -> None:
    """
    Refuse to emit rows that Monarch would silently drop on import.

    A row whose Date or Amount is blank is not an ordinary formatting problem:
    Monarch's importer skips it without surfacing a row-level error, so the
    migration looks like it worked while history is missing. The blank usually
    comes from a column header this script could not fold onto a canonical field,
    which is why the message names the required columns.

    Args:
        monarch_transactions (List[Dict[str, str]]): Transformed rows about to be written
        input_file (str): Source file, used to name the problem in the message
        max_listed (int): Cap on how many offending rows to enumerate

    Rows are reported by data-row number with the matching file line beside it
    (the header occupies the first line), so a number can be typed straight into
    a spreadsheet without an off-by-one.

    Raises:
        ValueError: If any row has a blank Date or Amount.
    """
    problems = []

    for row_number, monarch_row in enumerate(monarch_transactions, start=1):
        missing = [field for field in REQUIRED_FIELDS
                   if not str(monarch_row.get(field, '') or '').strip()]
        if missing:
            problems.append((row_number, missing))

    if not problems:
        return

    listed = '; '.join(
        f"data row {row_number}, file line {row_number + 1}: no {' and '.join(fields)}"
        for row_number, fields in problems[:max_listed]
    )
    hidden = f" (and {len(problems) - max_listed} more)" if len(problems) > max_listed else ''

    raise ValueError(
        f"{os.path.basename(input_file)}: {len(problems)} of {len(monarch_transactions)} rows "
        f"have no {' or '.join(REQUIRED_FIELDS)} value, and Monarch silently skips rows like "
        f"that instead of importing them. Nothing was written. This usually means the export's "
        f"column headers did not match the expected names "
        f"({', '.join(CANONICAL_FIELDS)}). Offending rows -> {listed}{hidden}"
    )


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
        ValueError: If the file has rows but no Date or Amount column
    """
    transactions = []
    
    try:
        # utf-8-sig strips a leading UTF-8 BOM. With plain 'utf-8' the BOM glues
        # itself onto the first header name ('\ufeffDate'), so every Date lookup
        # below silently returns '' for the whole file. newline='' is what the csv
        # module requires so that quoted fields may contain embedded line breaks.
        with open(input_file, 'r', encoding='utf-8-sig', newline='') as infile:
            reader = csv.DictReader(infile)
            raw_headers = list(reader.fieldnames or [])
            header_map, _unrecognized = canonicalize_headers(raw_headers)
            reader.fieldnames = [header_map[name] for name in raw_headers]
            missing_columns = [field for field in REQUIRED_FIELDS
                               if field not in (reader.fieldnames or [])]
            
            # Detect the Personal Capital format based on headers
            pc_format = detect_pc_format(reader.fieldnames or [])
            
            # Read all transactions into memory, re-keyed onto canonical fields
            for row in reader:
                transactions.append(canonicalize_row(row, header_map))
                
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {input_file}")
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(f"File encoding error in {input_file}: {e}")
    
    # An empty file is legitimately header-only, so only a file that actually
    # carries rows is refused for lacking the columns Monarch needs.
    if missing_columns and transactions:
        raise ValueError(
            f"{os.path.basename(input_file)}: no {' or '.join(missing_columns)} column in the "
            f"export (headers found: {', '.join(raw_headers)}). Refusing to write "
            f"{len(transactions)} rows whose {' or '.join(missing_columns)} would be blank, "
            f"because Monarch silently skips such rows. Expected column names: "
            f"{', '.join(CANONICAL_FIELDS)}."
        )

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
    
    # Try exact match first, then case-insensitive match if needed
    mapped_category = category_mappings.get(original_category)
    if mapped_category is None:
        # If no exact match, try case-insensitive lookup
        # This handles when category_mappings has lowercase keys due to case_sensitive_matching: false
        mapped_category = category_mappings.get(original_category.lower(), original_category)
    else:
        # Use the mapped category from exact match
        pass
    
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


def convert_pc_to_monarch(input_file: str, output_file: str, config_path: Optional[str] = None) -> Tuple[int, Dict]:
    """
    Convert a Personal Capital CSV file to Monarch Money import format.
    
    This is the main conversion function that orchestrates the entire process:
    1. Read and parse the Personal Capital CSV file
    2. Load category mappings from configuration file
    3. Transform each transaction to Monarch format
    4. Track category remapping statistics
    5. Write the output CSV file
    
    Args:
        input_file (str): Path to input Personal Capital CSV file
        output_file (str): Path where Monarch CSV should be written
        config_path (Optional[str]): Path to custom configuration file
    
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
    
    # Step 2: Get category mappings from configuration file
    category_mappings = get_category_mappings(config_path)
    
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
    
    # Step 4: Refuse to write anything Monarch would quietly drop rows from
    validate_monarch_rows(monarch_transactions, input_file)

    # Step 5: Write the Monarch CSV file
    write_monarch_csv(monarch_transactions, output_file)
    
    return len(monarch_transactions), remapping_counts


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert Personal Capital CSV exports to Monarch Money import format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_pc_to_monarch.py                           # Use defaults (./input, ./output)
  python migrate_pc_to_monarch.py -i data -o results       # Custom directories
  python migrate_pc_to_monarch.py --config my.yaml        # Custom config file
  python migrate_pc_to_monarch.py -i ~/Downloads -o ~/Desktop/monarch  # Absolute paths
  python migrate_pc_to_monarch.py --help                  # Show this help message

Directory Structure:
  The script processes all .csv files in the input directory and creates
  corresponding *-monarch.csv files in the output directory.

For more information, see the README.md file.
        """
    )
    
    parser.add_argument(
        '--input-dir', '-i',
        type=str,
        default='input',
        help='Input directory containing Personal Capital CSV files (default: ./input)',
        metavar='INPUT_DIR'
    )
    
    parser.add_argument(
        '--output-dir', '-o', 
        type=str,
        default='output',
        help='Output directory for converted Monarch CSV files (default: ./output)',
        metavar='OUTPUT_DIR'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to custom YAML configuration file (default: config.yaml)',
        metavar='CONFIG_FILE'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Personal Capital to Monarch Migration Script v2.0'
    )
    
    return parser.parse_args()


def main() -> None:
    """
    Main function to process all Personal Capital CSV files in the specified input folder.
    
    This function orchestrates the entire batch conversion process:
    1. Parses command-line arguments (including custom directories and config file path)
    2. Validates input/output directory structure
    3. Discovers Personal Capital CSV files to convert
    4. Processes each file through the conversion pipeline
    5. Provides detailed progress feedback and statistics
    6. Generates summary report of all conversions and category remappings
    
    Directory Structure:
        Input Directory:  Contains Personal Capital CSV exports
        Output Directory: Will contain Monarch-compatible CSV files (created if needed)
        
    File Naming Convention:
        Input:  any-filename.csv
        Output: any-filename-monarch.csv
        
    The function skips files that already have '-monarch.csv' suffix to avoid
    re-processing already converted files.
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Define directory paths from command-line arguments
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    # Step 1: Validate input directory exists
    if not input_dir.exists():
        print(f"❌ Error: Input directory '{input_dir}' not found!")
        print(f"Please create the directory '{input_dir}' and place your Personal Capital CSV files there.")
        print(f"Or use -i flag to specify a different input directory.")
        return
    
    # Step 2: Create output directory if it doesn't exist
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Input directory: {input_dir.absolute()}")
        print(f"📁 Output directory: {output_dir.absolute()}")
    except OSError as e:
        print(f"❌ Error creating output directory '{output_dir}': {e}")
        return
    
    # Step 3: Discover Personal Capital CSV files to process
    csv_files = glob.glob(str(input_dir / '*.csv'))
    pc_files = [f for f in csv_files if not f.endswith('-monarch.csv')]
    
    if not pc_files:
        print(f"⚠️ No Personal Capital CSV files found in '{input_dir}' directory!")
        print(f"Please place your Personal Capital transaction exports (.csv files) in the '{input_dir}' folder.")
        print(f"Or use -i flag to specify a different input directory containing your CSV files.")
        return
    
    # Step 4: Process each file and track overall statistics
    print(f"🔍 Found {len(pc_files)} Personal Capital CSV file(s) to convert:")
    
    total_transactions = 0  # Track total transactions across all files
    all_remappings = {}     # Accumulate category remapping statistics
    successful_conversions = 0
    failed_conversions = 0    # Files that produced no output at all
    
    for input_file in pc_files:
        # Generate output filename with -monarch suffix in output directory
        input_path = Path(input_file)
        output_filename = input_path.stem + '-monarch.csv'
        output_file = output_dir / output_filename
        
        print(f"\n📄 Processing: {input_path.name}")
        print(f"📤 Output: {output_filename}")
        
        try:
            # Convert the Personal Capital file to Monarch format
            transaction_count, remapping_counts = convert_pc_to_monarch(str(input_file), str(output_file), args.config)
            
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
            failed_conversions += 1
    
    # Step 5: Display comprehensive summary report
    failed_conversions = len(pc_files) - successful_conversions

    if failed_conversions:
        print(f"\n⚠️ Migration finished with problems!")
    else:
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

    # A run that wrote nothing must not look like a run that migrated everything.
    if failed_conversions:
        print(f"\n❌ {failed_conversions} of {len(pc_files)} file(s) produced no output. The "
              f"errors above name the headers each file actually had; nothing was written for "
              f"them. Exiting non-zero so a scripted migration cannot overlook this.")
        sys.exit(1)


if __name__ == "__main__":
    main()