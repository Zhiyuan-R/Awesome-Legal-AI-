"""
Field Processor using LLM
Handles intelligent deduplication, grouping, and conditional logic generation
using Claude AI.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from anthropic import Anthropic
import os


class FieldProcessor:
    """Processes extracted form fields using LLM for intelligent analysis."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the field processor.

        Args:
            api_key: Anthropic API key. If None, will use ANTHROPIC_API_KEY env variable.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-5-20250929"

    def process_fields(
        self,
        fields: List[Dict[str, Any]],
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Process all fields: deduplicate, group, and generate conditional logic.

        Args:
            fields: List of extracted field dictionaries
            batch_size: Number of fields to process in each batch

        Returns:
            Final processed field structure
        """
        print(f"\nProcessing {len(fields)} fields...")

        # Step 1: Deduplicate fields
        print("\n1. Deduplicating fields using LLM...")
        deduplicated_fields = self._deduplicate_fields(fields, batch_size)
        print(f"   Reduced to {len(deduplicated_fields)} unique fields")

        # Step 2: Group related fields
        print("\n2. Grouping related fields...")
        grouped_fields = self._group_fields(deduplicated_fields)

        # Step 3: Generate conditional logic and parent questions
        print("\n3. Generating conditional logic...")
        final_fields = self._generate_conditional_logic(grouped_fields)

        return final_fields

    def _deduplicate_fields(
        self,
        fields: List[Dict[str, Any]],
        batch_size: int
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to intelligently deduplicate similar fields.

        This handles variations like 'name', 'Name', 'Full Name' intelligently
        without being too strict (string matching) or too loose (embeddings).
        """
        if not fields:
            return []

        # Process in batches to avoid token limits
        all_deduplicated = []
        for i in range(0, len(fields), batch_size):
            batch = fields[i:i + batch_size]
            deduplicated_batch = self._deduplicate_batch(batch)
            all_deduplicated.extend(deduplicated_batch)

        return all_deduplicated

    def _deduplicate_batch(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate a single batch of fields."""
        # Prepare field summary for LLM
        field_summary = []
        for idx, field in enumerate(fields):
            field_summary.append({
                "index": idx,
                "field_name": field["field_name"],
                "source_pdf": field["source_pdf"],
                "type": field.get("field_type", "text")
            })

        prompt = f"""You are an expert at analyzing form fields. I have extracted fields from multiple PDF forms and need to identify which fields are duplicates or represent the same information.

Here are the fields:
{json.dumps(field_summary, indent=2)}

Your task:
1. Identify groups of fields that represent the SAME information (e.g., "Full Name", "Name", "Applicant Name" all mean the same thing)
2. Be intelligent - not too strict (don't require exact string match) but not too loose (don't merge "First Name" with "Full Name")
3. For each group, select the BEST field name to represent the group (clearest, most complete)

Return a JSON array of groups. Each group should have:
- "canonical_name": The best field name to use
- "field_indices": Array of indices from the input that belong to this group
- "reasoning": Brief explanation of why these are the same

Example output format:
[
  {{
    "canonical_name": "Full Name",
    "field_indices": [0, 5, 12],
    "reasoning": "All refer to the applicant's complete name"
  }},
  {{
    "canonical_name": "Date of Birth",
    "field_indices": [1],
    "reasoning": "Unique field, no duplicates"
  }}
]

Respond with ONLY the JSON array, no additional text."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse LLM response
        response_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        try:
            groups = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse LLM response: {e}")
            print(f"Response was: {response_text}")
            # Fallback: treat each field as unique
            return fields

        # Merge fields based on LLM grouping
        deduplicated = []
        for group in groups:
            indices = group["field_indices"]
            if not indices:
                continue

            # Use the first field as base and merge metadata
            base_field = fields[indices[0]].copy()
            base_field["field_name"] = group["canonical_name"]

            # Collect source PDFs
            sources = [fields[idx]["source_pdf"] for idx in indices]
            base_field["sources"] = list(set(sources))

            deduplicated.append(base_field)

        return deduplicated

    def _group_fields(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use LLM to group related fields together.

        For example: first_name, middle_name, last_name -> name group
        """
        if not fields:
            return []

        field_summary = []
        for idx, field in enumerate(fields):
            field_summary.append({
                "index": idx,
                "field_name": field["field_name"],
                "type": field.get("field_type", "text")
            })

        prompt = f"""You are an expert at organizing form fields. I need to group related fields together for better UI rendering.

Here are the fields:
{json.dumps(field_summary, indent=2)}

Your task:
1. Identify fields that should be grouped together (e.g., First Name, Middle Name, Last Name form a "name" group)
2. Common groups include: name, address, contact, employment, spouse, children, etc.
3. Each field should belong to exactly one group
4. Create meaningful group names

Return a JSON array where each element has:
- "group_name": Name of the group (e.g., "name", "address")
- "field_indices": Array of field indices that belong to this group
- "description": Brief description of what this group represents

Example:
[
  {{
    "group_name": "name",
    "field_indices": [0, 1, 2],
    "description": "Applicant's full name components"
  }},
  {{
    "group_name": "address",
    "field_indices": [3, 4, 5, 6, 7],
    "description": "Residential address fields"
  }}
]

Respond with ONLY the JSON array, no additional text."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        # Remove markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        try:
            groups = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse grouping response: {e}")
            # Fallback: each field in its own group
            groups = [{"group_name": f"group_{idx}", "field_indices": [idx], "description": ""}
                      for idx in range(len(fields))]

        # Add group information to fields (using group_id for order_index assignment later)
        grouped_fields = []
        for group_id, group in enumerate(groups):
            for field_idx in group["field_indices"]:
                if field_idx < len(fields):
                    field = fields[field_idx].copy()
                    field["_group_id"] = group_id  # Temporary, will be used for order_index
                    grouped_fields.append(field)

        return grouped_fields

    def _generate_conditional_logic(
        self,
        fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate conditional logic and parent-child relationships.

        Creates high-level questions that can filter which fields to show.
        """
        field_summary = []
        for idx, field in enumerate(fields):
            field_summary.append({
                "index": idx,
                "field_name": field["field_name"]
            })

        prompt = f"""You are an expert at designing smart forms. I need to create a decision tree for form fields to avoid showing irrelevant questions.

Here are the fields:
{json.dumps(field_summary, indent=2)}

Your task:
1. Identify patterns where multiple fields could be controlled by a single parent question
2. For example: if there are spouse1, spouse2... spouse6 fields, create a parent question "Are you married?" or "How many spouses?"
3. For example: if there are child1, child2... fields, create "Do you have children?" and "How many children?"
4. Create logical parent-child relationships WITH condition values

Return a JSON object with:
- "parent_questions": Array of new high-level questions to add
  Each has: {{
    "question_id": unique ID,
    "label": The question to ask,
    "type": "boolean", "number", or "choice",
    "options": (if type is choice)
  }}
- "field_relationships": Object mapping field indices to their condition
  Each has: {{
    "parent_id": parent question ID,
    "condition": {{
      "operator": "equals", "greater_than", "greater_or_equal", "less_than", "less_or_equal", "not_equals",
      "value": the value to compare against
    }}
  }}

Example:
{{
  "parent_questions": [
    {{
      "question_id": "are_you_married",
      "label": "Are you married?",
      "type": "boolean"
    }},
    {{
      "question_id": "num_children",
      "label": "How many children do you have?",
      "type": "number"
    }}
  ],
  "field_relationships": {{
    "5": {{
      "parent_id": "are_you_married",
      "condition": {{"operator": "equals", "value": true}}
    }},
    "6": {{
      "parent_id": "are_you_married",
      "condition": {{"operator": "equals", "value": true}}
    }},
    "10": {{
      "parent_id": "num_children",
      "condition": {{"operator": "greater_than", "value": 0}}
    }},
    "11": {{
      "parent_id": "num_children",
      "condition": {{"operator": "greater_or_equal", "value": 2}}
    }}
  }}
}}

Respond with ONLY the JSON object, no additional text."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        # Remove markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        try:
            conditional_logic = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse conditional logic: {e}")
            conditional_logic = {"parent_questions": [], "field_relationships": {}}

        # Build final output structure
        output = {}

        # Add parent questions first
        for parent_q in conditional_logic.get("parent_questions", []):
            q_id = parent_q["question_id"]
            output[q_id] = {
                "label": parent_q["label"],
                "type": parent_q["type"],
                "required": False,
                "options": parent_q.get("options"),
                "_metadata": {
                    "is_parent_question": True,
                    "generated": True
                }
            }

        # Add all fields with enhanced metadata
        relationships = conditional_logic.get("field_relationships", {})
        for idx, field in enumerate(fields):
            # Generate user-friendly label and explanation
            label_explanation = self._generate_label_and_explanation(field["field_name"])

            # Use _group_id for order_index (fields in same group get same order_index)
            order_index = field.get("_group_id", idx)

            # Extract parent relationship and condition
            relationship = relationships.get(str(idx))
            parent_id = None
            parent_condition = None

            if relationship:
                if isinstance(relationship, dict):
                    # New format with condition
                    parent_id = relationship.get("parent_id")
                    parent_condition = relationship.get("condition")
                else:
                    # Legacy format (just parent ID string)
                    parent_id = relationship

            field_key = field["field_name"]
            metadata = {
                "field_name": field["field_name"],
                "source_pdf": field.get("sources", [field.get("source_pdf")]),
                "order_index": order_index,
                "parent": parent_id,
                "position": None
            }

            # Add parent_condition if it exists
            if parent_condition:
                metadata["parent_condition"] = parent_condition

            output[field_key] = {
                "label": label_explanation["label"],
                "explanation": label_explanation["explanation"],
                "type": field.get("field_type", "text"),
                "required": field.get("required", False),
                "placeholder": f"Enter your {field['field_name'].lower()}",
                "_metadata": metadata
            }

            # Add options for choice fields
            if field.get("options"):
                output[field_key]["options"] = field["options"]

            # Add max_length for text fields
            if field.get("max_length"):
                output[field_key]["max_length"] = field["max_length"]

        return output

    def _generate_label_and_explanation(self, field_name: str) -> Dict[str, str]:
        """Generate user-friendly label and explanation for a field."""
        prompt = f"""Given the form field name "{field_name}", create:
1. A clear, user-friendly question/label
2. A helpful explanation that guides the user on how to fill it

Return JSON only:
{{
  "label": "question here",
  "explanation": "helpful explanation here"
}}

Make it clear and professional. For example:
- Field "DOB" -> label: "What is your date of birth?", explanation: "Enter your date of birth as it appears on your birth certificate (MM/DD/YYYY)"
- Field "Applicant Full Name" -> label: "What is your full name?", explanation: "Enter your complete legal name as it appears on official documents"

Respond with ONLY the JSON, no additional text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text.strip()

            # Remove markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
                if response_text.startswith("json"):
                    response_text = response_text[4:].strip()

            result = json.loads(response_text)
            return result

        except Exception as e:
            print(f"Warning: Failed to generate label for {field_name}: {e}")
            # Fallback
            return {
                "label": f"What is your {field_name.lower()}?",
                "explanation": f"Enter your {field_name.lower()}"
            }
