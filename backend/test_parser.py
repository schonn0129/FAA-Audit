#!/usr/bin/env python3
"""
Test script for the PDF parser.

Usage:
    python test_parser.py <path_to_pdf_file>
    
Example:
    python test_parser.py ../test_documents/sample.pdf
"""

import sys
import json
import os
from pdf_parser import FAAPDFParser, parse_pdf


def test_parser(pdf_path: str):
    """
    Test the PDF parser with a given PDF file.
    
    Args:
        pdf_path: Path to the PDF file to test
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        return
    
    if not pdf_path.lower().endswith('.pdf'):
        print(f"Error: File is not a PDF: {pdf_path}")
        return
    
    print(f"Testing PDF parser with: {pdf_path}")
    print("=" * 60)
    
    try:
        # Parse the PDF
        print("\n[1] Parsing PDF...")
        parsed_data = parse_pdf(pdf_path)
        
        # Display summary
        print("\n[2] Parsing Results Summary:")
        print("-" * 60)
        print(f"Total Pages: {parsed_data.get('metadata', {}).get('page_count', 0)}")
        print(f"Tables Found: {len(parsed_data.get('tables', []))}")
        print(f"Questions Found: {len(parsed_data.get('questions', []))}")
        print(f"Findings Found: {len(parsed_data.get('findings', []))}")
        print(f"Raw Text Length: {parsed_data.get('raw_text_length', 0)} characters")
        
        # Display metadata
        print("\n[3] Metadata:")
        print("-" * 60)
        metadata = parsed_data.get('metadata', {})
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        
        # Display questions
        print(f"\n[4] Questions ({len(parsed_data.get('questions', []))} found):")
        print("-" * 60)
        questions = parsed_data.get('questions', [])
        
        if questions:
            for idx, q in enumerate(questions[:10], 1):  # Show first 10
                print(f"\nQuestion {idx}:")
                print(f"  Element_ID: {q.get('Element_ID', 'N/A')}")
                print(f"  QID: {q.get('QID', 'N/A')}")
                print(f"  Question_Number: {q.get('Question_Number', 'N/A')}")
                print(f"  Question_Text_Full: {q.get('Question_Text_Full', 'N/A')[:100]}...")
                print(f"  PDF_Page_Number: {q.get('PDF_Page_Number', 'N/A')}")
                if q.get('Reference_CFR_List'):
                    print(f"  CFR References: {', '.join(q.get('Reference_CFR_List', []))}")
            
            if len(questions) > 10:
                print(f"\n... and {len(questions) - 10} more questions")
        else:
            print("  No questions found!")
        
        # Display tables summary
        print(f"\n[5] Tables ({len(parsed_data.get('tables', []))} found):")
        print("-" * 60)
        tables = parsed_data.get('tables', [])
        for idx, table in enumerate(tables[:5], 1):  # Show first 5
            print(f"\nTable {idx} (Page {table.get('page', 'N/A')}):")
            print(f"  Headers: {table.get('headers', [])}")
            print(f"  Rows: {table.get('row_count', 0)}")
        
        # Save full output to JSON file
        output_file = pdf_path.replace('.pdf', '_parsed.json')
        print(f"\n[6] Saving full output to: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved successfully!")
        
        # Display any notes/warnings
        print("\n[7] Notes/Warnings:")
        print("-" * 60)
        for q in questions:
            if q.get('Notes'):
                print(f"  Element {q.get('Element_ID', 'N/A')}: {', '.join(q.get('Notes', []))}")
        
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"\nError parsing PDF: {e}")
        import traceback
        traceback.print_exc()
        return


def debug_parser(pdf_path: str):
    """
    Run debug extraction to see what patterns are found.
    
    Args:
        pdf_path: Path to the PDF file
    """
    print(f"Running debug extraction on: {pdf_path}")
    print("=" * 60)
    
    try:
        with FAAPDFParser(pdf_path) as parser:
            debug_info = parser.debug_extract_patterns()
            
            print("\nDebug Information:")
            print("-" * 60)
            print(f"Total Lines: {debug_info.get('total_lines', 0)}")
            print(f"Total Characters: {debug_info.get('total_chars', 0)}")
            
            print(f"\nPotential Questions Found: {len(debug_info.get('potential_questions', []))}")
            for q in debug_info.get('potential_questions', [])[:5]:
                print(f"  Line {q['line']}: {q['text']}")
            
            print(f"\nNumbered Items Found: {len(debug_info.get('numbered_items', []))}")
            for item in debug_info.get('numbered_items', [])[:5]:
                print(f"  Line {item['line']}: {item['text']}")
            
            print(f"\nQuestion Marks Found: {len(debug_info.get('question_marks', []))}")
            for qm in debug_info.get('question_marks', [])[:5]:
                print(f"  Line {qm['line']}: {qm['text']}")
            
            print(f"\nTable Structures: {len(debug_info.get('table_structures', []))}")
            for table in debug_info.get('table_structures', [])[:3]:
                print(f"  Page {table['page']}: {table['headers']} ({table['row_count']} rows)")
                
    except Exception as e:
        print(f"Error in debug mode: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_parser.py <path_to_pdf_file> [--debug]")
        print("\nExample:")
        print("  python test_parser.py ../test_documents/sample.pdf")
        print("  python test_parser.py ../test_documents/sample.pdf --debug")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if len(sys.argv) > 2 and sys.argv[2] == "--debug":
        debug_parser(pdf_path)
    else:
        test_parser(pdf_path)
