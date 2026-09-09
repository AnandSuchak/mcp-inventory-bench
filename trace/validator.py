"""
JSON Schema Draft 2020-12 Validator for Tool Arguments
Project: mcp-inventory-bench
Author: Anand S. Suchak

Conforms to current Model Context Protocol (MCP) 2026-07-28 specifications.
Validates tool arguments against complete Draft 2020-12 JSON schemas and returns
structured ValidationErrorRecord instances without calling backend handlers.
"""

from typing import Dict, Any, List, Tuple
import jsonschema
from jsonschema.validators import Draft202012Validator
from trace.models import ValidationErrorRecord

class SchemaValidator:
    """Strict JSON Schema Draft 2020-12 argument validator."""

    def __init__(self, schema: Dict[str, Any]):
        self.raw_schema = schema
        # Instantiate validator
        Draft202012Validator.check_schema(schema)
        self.validator = Draft202012Validator(schema)

    def validate(self, arguments: Dict[str, Any]) -> Tuple[bool, List[ValidationErrorRecord]]:
        """
        Validate arguments against the schema.
        Returns:
            (is_valid: bool, errors: List[ValidationErrorRecord])
        """
        errors: List[ValidationErrorRecord] = []
        raw_errors = sorted(self.validator.iter_errors(arguments), key=lambda e: str(e.path))

        for err in raw_errors:
            # Format JSON pointer path, e.g. /vendor_id or /items/0/sku
            path_parts = list(err.path)
            if not path_parts:
                formatted_path = "/"
            else:
                formatted_path = "/" + "/".join(str(p) for p in path_parts)

            schema_path_str = "/".join(str(p) for p in err.schema_path)

            rec = ValidationErrorRecord(
                keyword=str(err.validator),
                path=formatted_path,
                message=err.message,
                schema_path=schema_path_str,
                failed_value=err.instance
            )
            errors.append(rec)

        return (len(errors) == 0, errors)

def validate_arguments(schema: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, List[ValidationErrorRecord]]:
    """Convenience function for stateless argument validation."""
    val = SchemaValidator(schema)
    return val.validate(arguments)
