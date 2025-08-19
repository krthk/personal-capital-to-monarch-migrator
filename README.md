# Personal Capital to Monarch Money Migration Tool

A comprehensive Python script that converts Personal Capital CSV transaction exports to the format required by Monarch Money, with complete category mapping support and flexible configuration options.

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install PyYAML
   ```

2. **Prepare your data:**
   - Export your Personal Capital transactions as CSV files
   - Place them in the `input/` directory (or specify custom directory with `-i`)

3. **Run the migration:**
   ```bash
   python migrate_pc_to_monarch.py
   ```

4. **Import to Monarch:**
   - Find converted files in the `output/` directory
   - In Monarch Money, go to each account → Edit → Upload transactions → Upload CSV
   - Select the corresponding `*-monarch.csv` file for each account

## 📁 Project Structure

```
pc-to-monarch-migration/
├── README.md                    # This file - user documentation
├── migrate_pc_to_monarch.py     # Main migration script
├── config.yaml                  # Category mapping configuration
├── requirements-dev.txt         # Development dependencies
├── tests/                       # Test suite
│   ├── test_migrate_pc_to_monarch.py    # Unit tests
│   ├── test_main_integration.py         # Integration tests
│   └── test_data/              # Test data files
├── input/                       # Default input directory (your PC CSV files)
├── output/                      # Default output directory (converted files)
└── archive/                     # Your archived transaction files
```

## 🔧 Command-Line Options

### Basic Usage
```bash
python migrate_pc_to_monarch.py [options]
```

### Available Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--help` | `-h` | Show help message and exit | |
| `--input-dir` | `-i` | Input directory containing PC CSV files | `./input` |
| `--output-dir` | `-o` | Output directory for Monarch CSV files | `./output` |
| `--config` | `-c` | Custom YAML configuration file | `./config.yaml` |
| `--version` | `-v` | Show version information | |

### Usage Examples

**Default directories:**
```bash
python migrate_pc_to_monarch.py
```

**Custom directories:**
```bash
python migrate_pc_to_monarch.py -i ~/Downloads/PC_Exports -o ~/Desktop/Monarch_Files
```

**Custom configuration:**
```bash
python migrate_pc_to_monarch.py --config my_custom_mappings.yaml
```

**Absolute paths:**
```bash
python migrate_pc_to_monarch.py -i /Users/name/Documents/PersonalCapital -o /Users/name/Documents/MonarchReady
```

## 📋 Supported Personal Capital Formats

The script automatically detects and handles two Personal Capital export formats:

### Format 1: Investment Accounts
- **Columns:** Date, Description, Category, Action, Quantity, Price, Amount
- **Use case:** Stock purchases, sales, dividends, investment transactions
- **Features:** Maps Action field to Monarch Notes column

### Format 2: Standard Accounts  
- **Columns:** Date, Description, Category, Tags, Amount
- **Use case:** Checking, credit card, standard transaction accounts
- **Features:** Preserves Tags field in Monarch format

## 🎯 Monarch Money Output Format

The script converts all transactions to Monarch's required 8-column format:

| Column | Description | Source |
|--------|-------------|--------|
| Date | Transaction date | PC Date |
| Merchant | Business/entity name | PC Description |
| Category | Expense/income category | PC Category (mapped) |
| Account | Account name | *Empty - assign in Monarch* |
| Original Statement | Original description | PC Description |
| Notes | Additional notes | PC Action (Format 1) |
| Amount | Transaction amount | PC Amount |
| Tags | Transaction tags | PC Tags (Format 2) |

## ⚙️ Category Mapping Configuration

### Complete Coverage
The included `config.yaml` provides mappings for **all 73 official Personal Capital categories**:
- **13 Income categories** (Consulting, Paychecks/Salary, etc.)
- **42 Expense categories** (Gasoline/Fuel, Healthcare/Medical, etc.)  
- **18 Other categories** (Transfers, Balance Adjustments, etc.)

### Configuration Structure
```yaml
category_mappings:
  # Personal Capital Category -> Monarch Money Category
  "Gasoline/Fuel": "Gas"
  "Healthcare/Medical": "Medical"
  "Credit Card Payments": "Credit Card Payment"
  # ... 200+ mappings
  
advanced:
  preserve_unmapped_categories: true
  case_sensitive_matching: false
  show_remapping_stats: true
```

### Customization
1. **Edit existing mappings:** Modify `config.yaml` to change how categories are mapped
2. **Add new mappings:** Add entries for any custom Personal Capital categories
3. **Create custom config:** Use `-c` flag to specify your own configuration file

### Key Features
- **Case-insensitive matching:** Works regardless of capitalization
- **Fallback system:** Preserves unmapped categories unchanged
- **Validation:** Comprehensive error checking and helpful messages
- **Statistics:** Shows category remapping summary after conversion

## 📊 What the Script Does

1. **🔍 Discovery:** Finds all `.csv` files in input directory
2. **📋 Format Detection:** Automatically identifies PC export format  
3. **🔄 Category Mapping:** Applies comprehensive category conversions
4. **✅ Validation:** Ensures data integrity and proper formatting
5. **📤 Export:** Creates Monarch-compatible CSV files with `-monarch` suffix
6. **📈 Reporting:** Provides detailed conversion statistics and remapping summary

### Processing Features
- **Batch Processing:** Handles multiple CSV files in one run
- **Skip Duplicates:** Ignores already-converted files (ending in `-monarch.csv`)
- **Error Handling:** Continues processing other files if one fails
- **Progress Tracking:** Shows detailed progress and statistics
- **Data Preservation:** Maintains all original transaction data

## 🧪 Testing

The project includes a comprehensive test suite with 35+ tests covering:

### Unit Tests
- Category mapping functionality
- Transaction transformation logic
- File format detection
- Data integrity validation
- Error handling scenarios

### Integration Tests
- End-to-end file conversion
- Directory management
- CLI argument processing
- Real data validation

### Run Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=migrate_pc_to_monarch --cov-report=html

# Test specific functionality
python -m pytest tests/test_migrate_pc_to_monarch.py -v
```

## 🛠️ Development Setup

### Prerequisites
- Python 3.7+
- PyYAML for configuration file parsing

### Installation
```bash
# Clone or download the project
git clone <repository-url>
cd pc-to-monarch-migration

# Install development dependencies
pip install -r requirements-dev.txt

# Verify installation
python migrate_pc_to_monarch.py --version
```

### Development Dependencies
- **PyYAML:** Configuration file parsing
- **pytest:** Testing framework
- **pytest-cov:** Test coverage reporting
- **pytest-mock:** Mock support for testing
- **flake8:** Code style checking

## 🔍 Troubleshooting

### Common Issues

**"Configuration file not found"**
- Ensure `config.yaml` exists in the project root
- Use `-c` flag to specify custom config file path
- Check file permissions

**"No Personal Capital CSV files found"**
- Verify CSV files are in the input directory
- Ensure files don't already end with `-monarch.csv`
- Use `-i` flag to specify correct input directory

**"Category mapping issues"**
- Check `config.yaml` for proper YAML syntax
- Verify category names match your PC export exactly
- Enable case-insensitive matching in config

**"Import errors in Monarch"**  
- Verify CSV files have exactly 8 columns
- Check date format compatibility
- Ensure amount fields are numeric

### Getting Help
1. **Check the help:** `python migrate_pc_to_monarch.py --help`
2. **Review configuration:** Examine `config.yaml` for mapping issues
3. **Test with sample data:** Use files in `tests/test_data/` to verify setup
4. **Run tests:** Execute test suite to verify installation

## 📈 Migration Statistics

After conversion, the script provides detailed statistics:
- **Files processed:** Number of CSV files converted
- **Total transactions:** Count of transactions migrated  
- **Category remappings:** Summary of how categories were transformed
- **Success rate:** Conversion success metrics

Example output:
```
🎉 Migration complete!
📊 Results Summary:
  • Files processed successfully: 3/3
  • Total transactions converted: 1,247
  • Output files saved in: /path/to/output

📋 Category Remapping Summary:
  • 156 transactions: 'Gasoline/Fuel' → 'Gas'
  • 89 transactions: 'Restaurants' → 'Restaurants & Bars'
  • 67 transactions: 'Groceries' → 'Groceries'
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional category mappings for edge cases
- Enhanced error handling and validation
- Support for additional Personal Capital export formats
- Performance optimizations for large datasets

## 📄 License

This project is provided as-is for personal use in migrating from Personal Capital to Monarch Money.

---

**Version:** 2.0  
**Last Updated:** 2025  
**Compatibility:** Personal Capital exports, Monarch Money imports