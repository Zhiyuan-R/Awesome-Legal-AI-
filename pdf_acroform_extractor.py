"""
PDF Acroform Extractor
Extracts form fields (acroforms) from PDF files.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import pypdf
from pypdf.generic import DictionaryObject


class PDFAcroformExtractor:
    """Extracts acroform fields from PDF files."""

    def __init__(self):
        self.extracted_fields = []

    def extract_from_file(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract acroform fields from a single PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of field dictionaries with metadata
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        fields = []

        try:
            with open(pdf_path, 'rb') as file:
                reader = pypdf.PdfReader(file)

                # Check if PDF has form fields
                if reader.get_form_text_fields() is None and reader.get_fields() is None:
                    print(f"Warning: No form fields found in {path.name}")
                    return fields

                # Get all fields
                form_fields = reader.get_fields()
                if form_fields:
                    for field_name, field_info in form_fields.items():
                        field_data = self._extract_field_info(
                            field_name,
                            field_info,
                            path.name
                        )
                        fields.append(field_data)

        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
            raise

        return fields

    def extract_from_multiple_files(self, pdf_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Extract acroform fields from multiple PDF files.

        Args:
            pdf_paths: List of paths to PDF files

        Returns:
            Combined list of all fields from all PDFs with metadata
        """
        all_fields = []

        for pdf_path in pdf_paths:
            print(f"Processing: {pdf_path}")
            fields = self.extract_from_file(pdf_path)
            all_fields.extend(fields)
            print(f"  Extracted {len(fields)} fields")

        print(f"\nTotal fields extracted: {len(all_fields)}")
        return all_fields

    def _extract_field_info(
        self,
        field_name: str,
        field_info: Any,
        source_pdf: str
    ) -> Dict[str, Any]:
        """
        Extract detailed information about a form field.

        Args:
            field_name: Name of the field
            field_info: Field information from pypdf
            source_pdf: Name of the source PDF file

        Returns:
            Dictionary with field information
        """
        field_data = {
            "field_name": field_name,
            "source_pdf": source_pdf,
            "field_type": self._get_field_type(field_info),
            "required": self._is_required(field_info),
            "value": self._get_field_value(field_info),
            "options": self._get_field_options(field_info),
            "max_length": self._get_max_length(field_info),
            "page": self._get_page_number(field_info),
        }

        return field_data

    def _get_field_type(self, field_info: Any) -> str:
        """Determine the type of form field."""
        if not isinstance(field_info, dict):
            return "text"

        field_type = field_info.get("/FT", "")

        type_mapping = {
            "/Tx": "text",
            "/Btn": "button",
            "/Ch": "choice",
            "/Sig": "signature"
        }

        return type_mapping.get(str(field_type), "text")

    def _is_required(self, field_info: Any) -> bool:
        """Check if field is required."""
        if not isinstance(field_info, dict):
            return False

        flags = field_info.get("/Ff", 0)
        # Bit 2 indicates required field
        return bool(flags & 2) if isinstance(flags, int) else False

    def _get_field_value(self, field_info: Any) -> Optional[str]:
        """Get the current value of the field."""
        if not isinstance(field_info, dict):
            return None

        value = field_info.get("/V")
        if value:
            return str(value)
        return None

    def _get_field_options(self, field_info: Any) -> Optional[List[str]]:
        """Get options for choice fields (dropdowns, radio buttons)."""
        if not isinstance(field_info, dict):
            return None

        # Check for /Opt (options array)
        opts = field_info.get("/Opt")
        if opts:
            if isinstance(opts, list):
                return [str(opt) for opt in opts]

        return None

    def _get_max_length(self, field_info: Any) -> Optional[int]:
        """Get maximum length for text fields."""
        if not isinstance(field_info, dict):
            return None

        max_len = field_info.get("/MaxLen")
        if max_len:
            return int(max_len)
        return None

    def _get_page_number(self, field_info: Any) -> Optional[int]:
        """Get the page number where the field appears."""
        # This is more complex and may not always be available
        # pypdf doesn't always provide easy access to page numbers
        # We'll return None for now, but this could be enhanced
        return None


def extract_acroforms(pdf_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Convenience function to extract acroforms from multiple PDFs.

    Args:
        pdf_paths: List of paths to PDF files

    Returns:
        List of all extracted fields
    """
    extractor = PDFAcroformExtractor()
    return extractor.extract_from_multiple_files(pdf_paths)
