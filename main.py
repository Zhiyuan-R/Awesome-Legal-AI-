#!/usr/bin/env python3
"""
PDF Acroform Extractor - Main Script

Extracts acroforms from multiple PDFs and intelligently combines them
using LLM-based deduplication, grouping, and conditional logic generation.

Usage:
    python main.py <pdf1> <pdf2> ... [--output output.json]
    python main.py --input-list pdfs.txt [--output output.json]

Example:
    python main.py form1.pdf form2.pdf --output combined_forms.json
    python main.py --input-list my_pdfs.txt --output result.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from pdf_acroform_extractor import extract_acroforms
from field_processor import FieldProcessor


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract and intelligently combine acroforms from multiple PDFs"
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "pdf_files",
        nargs="*",
        help="PDF files to process"
    )
    input_group.add_argument(
        "--input-list",
        type=str,
        help="Text file containing list of PDF paths (one per line)"
    )

    # Output option
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="combined_forms.json",
        help="Output JSON file (default: combined_forms.json)"
    )

    # API key option
    parser.add_argument(
        "--api-key",
        type=str,
        help="Anthropic API key (or set ANTHROPIC_API_KEY env variable)"
    )

    # Batch size option
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of fields to process per LLM batch (default: 50)"
    )

    # Skip processing option
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Only extract fields, skip LLM processing"
    )

    return parser.parse_args()


def load_pdf_paths(args) -> List[str]:
    """Load PDF paths from arguments."""
    if args.input_list:
        # Load from file
        input_file = Path(args.input_list)
        if not input_file.exists():
            print(f"Error: Input list file not found: {args.input_list}")
            sys.exit(1)

        with open(input_file, 'r') as f:
            paths = [line.strip() for line in f if line.strip()]

    else:
        # Use direct arguments
        paths = args.pdf_files

    # Validate paths
    valid_paths = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            print(f"Warning: PDF not found, skipping: {path}")
        elif not p.suffix.lower() == '.pdf':
            print(f"Warning: Not a PDF file, skipping: {path}")
        else:
            valid_paths.append(str(p))

    if not valid_paths:
        print("Error: No valid PDF files to process")
        sys.exit(1)

    return valid_paths


def main():
    """Main execution function."""
    # Load environment variables
    load_dotenv()

    # Parse arguments
    args = parse_arguments()

    # Load PDF paths
    pdf_paths = load_pdf_paths(args)

    print(f"PDF Acroform Extractor")
    print(f"=" * 60)
    print(f"Processing {len(pdf_paths)} PDF file(s)")
    print(f"Output: {args.output}")
    print(f"=" * 60)

    # Step 1: Extract acroforms from PDFs
    print("\n[STEP 1] Extracting acroforms from PDFs...")
    try:
        extracted_fields = extract_acroforms(pdf_paths)
    except Exception as e:
        print(f"Error extracting acroforms: {e}")
        sys.exit(1)

    if not extracted_fields:
        print("No fields extracted from PDFs. Exiting.")
        sys.exit(0)

    # If extract-only mode, save raw extraction and exit
    if args.extract_only:
        raw_output = {
            "total_fields": len(extracted_fields),
            "fields": extracted_fields
        }
        with open(args.output, 'w') as f:
            json.dump(raw_output, f, indent=2)
        print(f"\n✓ Raw extraction saved to {args.output}")
        return

    # Step 2: Process fields with LLM
    print("\n[STEP 2] Processing fields with LLM...")
    try:
        processor = FieldProcessor(api_key=args.api_key)
        combined_forms = processor.process_fields(
            extracted_fields,
            batch_size=args.batch_size
        )
    except Exception as e:
        print(f"Error processing fields: {e}")
        sys.exit(1)

    # Step 3: Save output
    print(f"\n[STEP 3] Saving output to {args.output}...")
    try:
        with open(args.output, 'w') as f:
            json.dump(combined_forms, f, indent=2)
        print(f"✓ Successfully saved {len(combined_forms)} fields to {args.output}")
    except Exception as e:
        print(f"Error saving output: {e}")
        sys.exit(1)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total fields extracted: {len(extracted_fields)}")
    print(f"Final combined fields: {len(combined_forms)}")

    # Count parent questions
    parent_count = sum(1 for v in combined_forms.values()
                       if v.get("_metadata", {}).get("is_parent_question"))
    print(f"Generated parent questions: {parent_count}")

    # Count groups
    groups = set()
    for v in combined_forms.values():
        group = v.get("_metadata", {}).get("group")
        if group:
            groups.add(group)
    print(f"Field groups: {len(groups)}")

    print("\n✓ Processing complete!")


if __name__ == "__main__":
    main()
