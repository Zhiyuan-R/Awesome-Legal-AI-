#!/usr/bin/env python3
"""
Example usage of the PDF Acroform Extractor

This script demonstrates how to use the tool programmatically.
"""

import json
from pathlib import Path
from dotenv import load_dotenv

from pdf_acroform_extractor import PDFAcroformExtractor
from field_processor import FieldProcessor


def example_basic_extraction():
    """
    Example 1: Basic extraction without LLM processing.
    """
    print("=" * 60)
    print("Example 1: Basic Extraction")
    print("=" * 60)

    # Create extractor
    extractor = PDFAcroformExtractor()

    # Extract from a single PDF
    # fields = extractor.extract_from_file("path/to/your/form.pdf")

    # Or extract from multiple PDFs
    pdf_files = [
        "form1.pdf",
        "form2.pdf",
        "form3.pdf"
    ]

    # Note: This will fail if PDFs don't exist - replace with your actual PDFs
    try:
        fields = extractor.extract_from_multiple_files(pdf_files)

        print(f"\nExtracted {len(fields)} fields")
        print("\nFirst field:")
        print(json.dumps(fields[0], indent=2))

        # Save raw extraction
        with open("raw_extraction.json", "w") as f:
            json.dump(fields, f, indent=2)
        print("\nRaw extraction saved to: raw_extraction.json")

    except FileNotFoundError as e:
        print(f"\n⚠️  PDFs not found: {e}")
        print("This is just an example. Replace with your actual PDF paths.")


def example_full_processing():
    """
    Example 2: Full processing with LLM-based deduplication, grouping, and conditional logic.
    """
    print("\n" + "=" * 60)
    print("Example 2: Full Processing with LLM")
    print("=" * 60)

    # Load environment variables
    load_dotenv()

    pdf_files = [
        "form1.pdf",
        "form2.pdf",
        "form3.pdf"
    ]

    try:
        # Step 1: Extract fields
        print("\nStep 1: Extracting fields from PDFs...")
        extractor = PDFAcroformExtractor()
        fields = extractor.extract_from_multiple_files(pdf_files)
        print(f"Extracted {len(fields)} fields")

        # Step 2: Process with LLM
        print("\nStep 2: Processing with LLM...")
        processor = FieldProcessor()  # Uses ANTHROPIC_API_KEY from .env
        combined_forms = processor.process_fields(fields, batch_size=50)

        # Step 3: Save results
        print("\nStep 3: Saving results...")
        with open("combined_forms.json", "w") as f:
            json.dump(combined_forms, f, indent=2)

        print(f"\n✓ Successfully processed {len(combined_forms)} fields")
        print("Output saved to: combined_forms.json")

        # Print summary
        parent_count = sum(
            1 for v in combined_forms.values()
            if v.get("_metadata", {}).get("is_parent_question")
        )
        print(f"\nGenerated {parent_count} parent questions")

        groups = set()
        for v in combined_forms.values():
            group = v.get("_metadata", {}).get("group")
            if group:
                groups.add(group)
        print(f"Created {len(groups)} field groups: {', '.join(sorted(groups))}")

    except FileNotFoundError as e:
        print(f"\n⚠️  PDFs not found: {e}")
        print("This is just an example. Replace with your actual PDF paths.")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def example_custom_processing():
    """
    Example 3: Custom processing with specific batch sizes and options.
    """
    print("\n" + "=" * 60)
    print("Example 3: Custom Processing")
    print("=" * 60)

    load_dotenv()

    try:
        # Extract fields
        extractor = PDFAcroformExtractor()
        fields = extractor.extract_from_multiple_files(["form1.pdf"])

        # Process with custom batch size
        processor = FieldProcessor()
        combined_forms = processor.process_fields(
            fields,
            batch_size=30  # Smaller batches for more precise control
        )

        # You can also access individual processing steps:
        # deduplicated = processor._deduplicate_fields(fields, batch_size=30)
        # grouped = processor._group_fields(deduplicated)

        print(f"\n✓ Processed {len(combined_forms)} fields with custom settings")

    except Exception as e:
        print(f"\n⚠️  {e}")


def example_analyze_output():
    """
    Example 4: Analyze the output structure.
    """
    print("\n" + "=" * 60)
    print("Example 4: Analyzing Output")
    print("=" * 60)

    # Load previously generated output
    output_file = "combined_forms.json"
    if not Path(output_file).exists():
        print(f"\n⚠️  {output_file} not found. Run example 2 first.")
        return

    with open(output_file, "r") as f:
        forms = json.load(f)

    # Analyze structure
    print(f"\nTotal fields: {len(forms)}")

    # Group by type
    type_counts = {}
    for field in forms.values():
        field_type = field.get("type", "unknown")
        type_counts[field_type] = type_counts.get(field_type, 0) + 1

    print("\nFields by type:")
    for field_type, count in sorted(type_counts.items()):
        print(f"  {field_type}: {count}")

    # Group by group
    group_counts = {}
    for field in forms.values():
        group = field.get("_metadata", {}).get("group")
        if group:
            group_counts[group] = group_counts.get(group, 0) + 1

    print("\nFields by group:")
    for group, count in sorted(group_counts.items()):
        print(f"  {group}: {count}")

    # Find conditional fields
    conditional_fields = [
        name for name, field in forms.items()
        if field.get("_metadata", {}).get("parent")
    ]
    print(f"\nConditional fields: {len(conditional_fields)}")
    if conditional_fields:
        print("Examples:")
        for name in conditional_fields[:3]:
            parent = forms[name]["_metadata"]["parent"]
            print(f"  • {name} (depends on {parent})")

    # Find parent questions
    parent_questions = [
        name for name, field in forms.items()
        if field.get("_metadata", {}).get("is_parent_question")
    ]
    print(f"\nParent questions: {len(parent_questions)}")
    if parent_questions:
        print("Examples:")
        for name in parent_questions[:3]:
            label = forms[name]["label"]
            print(f"  • {name}: {label}")


if __name__ == "__main__":
    print("\nPDF Acroform Extractor - Example Usage")
    print("=" * 60)
    print("\nThis script demonstrates various ways to use the tool.")
    print("Note: Examples will fail if PDF files don't exist.")
    print("\n" + "=" * 60)

    # Run examples
    # Uncomment the ones you want to try:

    # example_basic_extraction()
    # example_full_processing()
    # example_custom_processing()
    # example_analyze_output()

    print("\n" + "=" * 60)
    print("To run examples, uncomment them in the main block.")
    print("=" * 60)
