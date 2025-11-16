# PDF Acroform Extractor

An intelligent tool that extracts acroforms (form fields) from multiple PDF files and combines them into a unified JSON structure using AI-powered deduplication, grouping, and conditional logic generation.

## Features

### 1. **PDF Acroform Extraction**
- Extracts all form fields from PDF files
- Supports text fields, checkboxes, radio buttons, dropdowns, and signatures
- Preserves field metadata (type, required status, options, max length, etc.)

### 2. **AI-Powered Deduplication**
- Uses Claude AI to intelligently identify duplicate fields across PDFs
- Handles variations like "name", "Name", "Full Name", "Applicant Name"
- **Not too strict**: Doesn't require exact string matching
- **Not too loose**: Won't merge "First Name" with "Full Name"
- Language model understands semantic meaning

### 3. **Smart Field Grouping**
- Automatically groups related fields together for rendering
- Related fields are assigned the same `order_index` value
- Examples:
  - First Name, Middle Name, Last Name → all get `order_index: 0`
  - Street, Apt, City, State, ZIP → all get `order_index: 1`
  - Phone, Email, Fax → all get `order_index: 2`
- Fields with the same `order_index` should be rendered together in the UI

### 4. **Conditional Logic Generation**
- Identifies patterns and creates decision tree logic
- Generates high-level parent questions to filter fields
- Examples:
  - "Are you married?" → controls spouse fields
  - "How many children do you have?" → controls child fields
  - "Are you employed?" → controls employment fields
- Tracks parent-child relationships in metadata

### 5. **Enhanced Field Metadata**
- User-friendly labels and explanations
- Source PDF tracking
- Field positioning and ordering
- Type information and validation rules

## Installation

### Prerequisites
- Python 3.8 or higher
- Anthropic API key ([Get one here](https://console.anthropic.com/))

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/Awesome-Legal-AI-.git
cd Awesome-Legal-AI-
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure API key**
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your Anthropic API key
nano .env
```

## Usage

### Basic Usage

Extract and process acroforms from multiple PDFs:

```bash
python main.py form1.pdf form2.pdf form3.pdf --output combined_forms.json
```

### Using an Input List

Create a text file with PDF paths (one per line):

```text
# pdfs.txt
/path/to/form1.pdf
/path/to/form2.pdf
/path/to/form3.pdf
```

Then run:

```bash
python main.py --input-list pdfs.txt --output result.json
```

### Command Line Options

```bash
python main.py [OPTIONS] <pdf_files...>

Options:
  pdf_files              One or more PDF files to process
  --input-list FILE      Text file with PDF paths (one per line)
  --output, -o FILE      Output JSON file (default: combined_forms.json)
  --api-key KEY          Anthropic API key (or set ANTHROPIC_API_KEY env var)
  --batch-size N         Fields per LLM batch (default: 50)
  --extract-only         Only extract fields, skip LLM processing
  -h, --help             Show help message
```

### Examples

**Process multiple PDFs with custom output:**
```bash
python main.py i-485.pdf i-130.pdf g-1145.pdf -o immigration_forms.json
```

**Extract only (skip AI processing):**
```bash
python main.py form.pdf --extract-only -o raw_fields.json
```

**Use custom batch size for large form sets:**
```bash
python main.py *.pdf --batch-size 30 -o forms.json
```

## Output Format

The tool generates a JSON file with the following structure:

```json
{
  "are_you_married": {
    "label": "Are you married?",
    "type": "boolean",
    "required": false,
    "options": null,
    "_metadata": {
      "is_parent_question": true,
      "generated": true
    }
  },
  "Applicant/Petitioner Full Last Name": {
    "label": "What is your full last name?",
    "explanation": "Enter your complete last name as it appears on official documents like your passport or birth certificate.",
    "type": "text",
    "required": false,
    "placeholder": "Enter your applicant/petitioner full last name",
    "_metadata": {
      "field_name": "Applicant/Petitioner Full Last Name",
      "source_pdf": ["g-1145.pdf", "i-485.pdf"],
      "order_index": 0,
      "parent": null,
      "position": null
    }
  },
  "First Name": {
    "label": "What is your first name?",
    "explanation": "Enter your legal first name exactly as it appears on your birth certificate.",
    "type": "text",
    "required": true,
    "placeholder": "Enter your first name",
    "_metadata": {
      "field_name": "First Name",
      "source_pdf": ["i-485.pdf"],
      "order_index": 0,
      "parent": null,
      "position": null
    }
  },
  "Middle Name": {
    "label": "What is your middle name?",
    "explanation": "Enter your middle name if you have one.",
    "type": "text",
    "required": false,
    "placeholder": "Enter your middle name",
    "_metadata": {
      "field_name": "Middle Name",
      "source_pdf": ["i-485.pdf"],
      "order_index": 0,
      "parent": null,
      "position": null
    }
  },
  "Spouse Name": {
    "label": "What is your spouse's name?",
    "explanation": "Enter your spouse's full legal name.",
    "type": "text",
    "required": false,
    "placeholder": "Enter your spouse name",
    "_metadata": {
      "field_name": "Spouse Name",
      "source_pdf": ["i-485.pdf"],
      "order_index": 5,
      "parent": "are_you_married",
      "position": null
    }
  }
}
```

### Field Structure

Each field has:
- **label**: User-friendly question
- **explanation**: Helpful guidance for filling the field
- **type**: Field type (text, boolean, choice, number, etc.)
- **required**: Whether the field is required
- **placeholder**: Placeholder text
- **options**: For choice fields (dropdowns, radio buttons)
- **max_length**: Maximum character length (for text fields)
- **_metadata**: Additional metadata
  - **field_name**: Original field name from PDF
  - **source_pdf**: Source PDF file(s) (array if field appears in multiple PDFs)
  - **order_index**: Rendering order - fields with the same order_index should be rendered together as a group
  - **parent**: ID of parent question (for conditional fields)
  - **position**: Field position coordinates (if available)
  - **is_parent_question**: True if this is a generated parent question (only for parent questions)
  - **generated**: True if field was generated (not from PDF) (only for parent questions)

**Note**: Fields with the same `order_index` belong to the same logical group and should be rendered together. For example, "First Name", "Middle Name", and "Last Name" would all have `order_index: 0`.

## How It Works

### 1. Extraction Phase
The tool uses `pypdf` to extract acroform fields from each PDF, capturing:
- Field names
- Field types (text, checkbox, dropdown, etc.)
- Current values
- Options (for choice fields)
- Required status
- Maximum length constraints

### 2. Deduplication Phase
Claude AI analyzes all extracted fields and:
- Groups semantically similar fields (e.g., "Name", "Full Name", "Applicant Name")
- Selects the best canonical name for each group
- Merges metadata while preserving source PDF information
- Avoids over-merging (won't combine "First Name" and "Last Name")

### 3. Grouping Phase
Claude AI identifies related fields and:
- Identifies which fields should be rendered together (e.g., name components, address components)
- Assigns the same `order_index` to fields that belong together
- Creates logical groupings for optimal form rendering

### 4. Conditional Logic Phase
Claude AI analyzes field patterns and:
- Identifies conditional relationships (e.g., spouse fields only if married)
- Generates high-level parent questions
- Creates parent-child mappings
- Builds decision tree structure

### 5. Enhancement Phase
For each field, Claude AI generates:
- Clear, user-friendly labels
- Helpful explanations
- Appropriate placeholders

## Use Cases

### Immigration Forms
Combine multiple USCIS forms (I-485, I-130, G-1145, etc.) into a unified questionnaire.

### Legal Documents
Merge similar legal forms from different jurisdictions.

### Healthcare Forms
Consolidate patient intake forms from multiple providers.

### Employment Applications
Combine job application forms from various sources.

### Government Forms
Unify tax forms, permit applications, and other government paperwork.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                              │
│                   (Orchestrator)                            │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ▼                                ▼
┌────────────────────────┐      ┌────────────────────────────┐
│  pdf_acroform_         │      │  field_processor.py        │
│  extractor.py          │      │  (LLM Processing)          │
│                        │      │                            │
│  • Extract fields      │      │  • Deduplicate fields      │
│  • Parse metadata      │      │  • Group related fields    │
│  • Handle field types  │      │  • Generate conditions     │
│                        │      │  • Create labels           │
└────────────────────────┘      └────────────────────────────┘
             │                                │
             └────────────┬───────────────────┘
                          ▼
                ┌──────────────────┐
                │  combined_forms  │
                │     .json        │
                └──────────────────┘
```

## API Usage

You can also use the components programmatically:

```python
from pdf_acroform_extractor import extract_acroforms
from field_processor import FieldProcessor

# Extract fields
pdf_files = ["form1.pdf", "form2.pdf"]
fields = extract_acroforms(pdf_files)

# Process with LLM
processor = FieldProcessor(api_key="your-api-key")
combined = processor.process_fields(fields, batch_size=50)

# Save result
import json
with open("output.json", "w") as f:
    json.dump(combined, f, indent=2)
```

## Cost Considerations

The tool uses Claude Sonnet 4.5 for LLM processing. Costs depend on:
- Number of fields extracted
- Batch size (smaller batches = more API calls)
- Complexity of forms

**Estimated costs:**
- Small form set (50 fields): ~$0.10 - $0.20
- Medium form set (200 fields): ~$0.40 - $0.80
- Large form set (500+ fields): ~$1.00 - $2.00

Use `--extract-only` flag to extract fields without LLM processing if you want to avoid API costs.

## Limitations

- PDF must have actual acroform fields (not just fillable text on images)
- Very complex conditional logic may require manual review
- Field position coordinates may not always be available
- Some PDF security features may block field extraction

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

## Acknowledgments

- Built with [pypdf](https://github.com/py-pdf/pypdf) for PDF processing
- Powered by [Claude AI](https://www.anthropic.com/claude) for intelligent field analysis
- Uses [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
