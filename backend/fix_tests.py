#!/usr/bin/env python3
"""
Script to automatically fix test files to use authenticated_client fixture.
"""
import re
from pathlib import Path

def fix_test_file(filepath: Path) -> bool:
    """Fix a single test file."""
    content = filepath.read_text()
    original_content = content
    
    # Remove TestClient imports and instantiation
    content = re.sub(
        r'from fastapi\.testclient import TestClient\n',
        '',
        content
    )
    
    content = re.sub(
        r'from app\.main import app\n',
        '',
        content
    )
    
    content = re.sub(
        r'client = TestClient\(app\)\n+',
        '',
        content
    )
    
    # Fix method signatures to accept client parameter
    # Match def test_xxx(self): and add client parameter
    def add_client_param(match):
        method_def = match.group(0)
        if '(self)' in method_def:
            return method_def.replace('(self):', '(self, client):')
        return method_def
    
    content = re.sub(
        r'def test_\w+\(self\):',
        add_client_param,
        content
    )
    
    # Write back if changed
    if content != original_content:
        filepath.write_text(content)
        return True
    return False

def main():
    """Process all test files."""
    tests_dir = Path(__file__).parent / 'tests'
    
    test_files = [
        tests_dir / 'test_contract_parser_api.py',
        tests_dir / 'test_document_matrix_api.py',
    ]
    
    for test_file in test_files:
        if test_file.exists():
            print(f"Processing {test_file.name}...")
            if fix_test_file(test_file):
                print(f"  ✅ Fixed {test_file.name}")
            else:
                print(f"  ⏭️  No changes needed for {test_file.name}")
        else:
            print(f"  ⚠️  File not found: {test_file}")
    
    print("\n✅ All test files processed!")

if __name__ == '__main__':
    main()
