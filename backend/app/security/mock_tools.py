from __future__ import annotations

from typing import Any


def execute_mock_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Return sandbox-only output. This module never contacts external systems."""
    if tool_name == "read_file":
        name = str(arguments.get("file_name", "invoice-demo.pdf"))
        return {
            "status": "SIMULATED",
            "message": f"Read completed in the local demo sandbox: {name}",
            "preview": "Invoice INV-DEMO-1042 | Vendor: Northwind Demo Ltd. | Total: $1,250.00",
        }
    if tool_name == "search_documents":
        return {
            "status": "SIMULATED",
            "message": "Search completed in the local demo sandbox.",
            "results": ["invoice-demo.pdf", "travel-policy-demo.pdf"],
        }
    if tool_name == "send_email":
        return {
            "status": "SIMULATED_NOT_SENT",
            "message": "Email delivery is disabled in this MVP. No email was sent.",
        }
    return {
        "status": "SIMULATED",
        "message": f"{tool_name} would be invoked in a connected integration; no external action was performed.",
    }
