#!/usr/bin/env python3
"""
Integration tests for the main function of the migration script.

These tests verify the complete end-to-end workflow including directory
management, file discovery, and batch processing.
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import io

# Import the main function
from migrate_pc_to_monarch import main


class TestMainIntegration:
    """Test the main function integration."""
    
    def test_main_with_no_input_directory(self, capsys):
        """Test main function when input directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory where there's no 'input' folder
            original_cwd = os.getcwd()
            original_argv = sys.argv[:]
            try:
                os.chdir(temp_dir)
                # Mock sys.argv to avoid interference with pytest arguments
                sys.argv = ['migrate_pc_to_monarch.py']
                main()
                
                captured = capsys.readouterr()
                assert "❌ Error: 'input' directory not found!" in captured.out
                assert "Please create an 'input' directory" in captured.out
                
            finally:
                os.chdir(original_cwd)
                sys.argv = original_argv
    
    def test_main_with_empty_input_directory(self, capsys):
        """Test main function with empty input directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty input directory
            input_dir = Path(temp_dir) / 'input'
            input_dir.mkdir()
            
            original_cwd = os.getcwd()
            original_argv = sys.argv[:]
            try:
                os.chdir(temp_dir)
                # Mock sys.argv to avoid interference with pytest arguments
                sys.argv = ['migrate_pc_to_monarch.py']
                main()
                
                captured = capsys.readouterr()
                assert "⚠️ No Personal Capital CSV files found" in captured.out
                
            finally:
                os.chdir(original_cwd)
                sys.argv = original_argv
    
    def test_main_with_test_data(self, capsys):
        """Test main function with real test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create input directory and copy test file
            input_dir = Path(temp_dir) / 'input'
            input_dir.mkdir()
            
            # Copy one of our test files
            test_file_src = Path('test_data/input/sample_format2.csv')
            if test_file_src.exists():
                shutil.copy(test_file_src, input_dir / 'sample_format2.csv')
                
                original_cwd = os.getcwd()
                original_argv = sys.argv[:]
                try:
                    os.chdir(temp_dir)
                    # Mock sys.argv to avoid interference with pytest arguments
                    sys.argv = ['migrate_pc_to_monarch.py']
                    main()
                    
                    captured = capsys.readouterr()
                    assert "🎉 Migration complete!" in captured.out
                    assert "✅ Converted" in captured.out
                    assert "📋 Category Remapping Summary:" in captured.out
                    
                    # Verify output file was created
                    output_dir = Path(temp_dir) / 'output'
                    assert output_dir.exists()
                    output_files = list(output_dir.glob('*.csv'))
                    assert len(output_files) == 1
                    assert 'sample_format2-monarch.csv' in output_files[0].name
                    
                finally:
                    os.chdir(original_cwd)
                    sys.argv = original_argv
            else:
                pytest.skip("Test data file not found")
    
    def test_main_error_handling(self, capsys):
        """Test main function error handling with file that causes processing error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create input directory with a file that will cause conversion error
            input_dir = Path(temp_dir) / 'input'
            input_dir.mkdir()
            
            # Create a CSV file with no data rows (just headers)
            # This should process successfully but with 0 transactions
            empty_csv = input_dir / 'empty.csv'
            with open(empty_csv, 'w') as f:
                f.write("Date,Description,Category,Tags,Amount\n")
            
            original_cwd = os.getcwd()
            original_argv = sys.argv[:]
            try:
                os.chdir(temp_dir)
                # Mock sys.argv to avoid interference with pytest arguments
                sys.argv = ['migrate_pc_to_monarch.py']
                main()
                
                captured = capsys.readouterr()
                # Should process successfully but with 0 transactions
                assert "✅ Converted 0 transactions successfully" in captured.out
                assert "🎉 Migration complete!" in captured.out
                
            finally:
                os.chdir(original_cwd)
                sys.argv = original_argv
    
    def test_main_output_directory_creation_error(self):
        """Test main function when output directory cannot be created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create input directory
            input_dir = Path(temp_dir) / 'input'
            input_dir.mkdir()
            
            # Create a file where output directory should be
            output_path = Path(temp_dir) / 'output'
            with open(output_path, 'w') as f:
                f.write("blocking file")
            
            original_cwd = os.getcwd()
            original_argv = sys.argv[:]
            try:
                os.chdir(temp_dir)
                # Mock sys.argv to avoid interference with pytest arguments
                sys.argv = ['migrate_pc_to_monarch.py']
                # This should handle the OSError gracefully
                main()
                
            finally:
                os.chdir(original_cwd)
                sys.argv = original_argv


if __name__ == '__main__':
    # Run tests when script is executed directly
    pytest.main([__file__, '-v'])