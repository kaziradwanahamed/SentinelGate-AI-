"""Local MCP server exposing sandbox tools protected by SentinelGate policies."""
from __future__ import annotations

from mcp.server import MCPServer

from app.schemas import AnalyzeRequest
from app.security.mock_tools import execute_mock_tool
from app.security.policy import evaluate_tool_call

mcp = MCPServer("SentinelGate Protected Tools")


def _guard(tool_name: str, arguments: dict, provenance: str = "trusted") -> dict:
    request = AnalyzeRequest(
        agent_id="claude-mcp-demo",
        user_goal=f"MCP host requested tool {tool_name}",
        tool_name=tool_name,
        tool_arguments=arguments,
        provenance=provenance,
    )
    decision = evaluate_tool_call(request)
    if decision["decision"] != "ALLOW":
        return {
            "decision": decision["decision"],
            "risk_score": decision["risk_score"],
            "reasons": decision["reasons"],
            "execution": "NOT_EXECUTED",
        }
    return {
        "decision": "ALLOW",
        "risk_score": decision["risk_score"],
        "execution": execute_mock_tool(tool_name, arguments),
    }


@mcp.tool()
def read_file(file_name: str) -> dict:
    """Read a harmless demo file through SentinelGate's policy check."""
    return _guard("read_file", {"file_name": file_name})


@mcp.tool()
def search_documents(query: str) -> dict:
    """Search the local demo document catalogue through SentinelGate."""
    return _guard("search_documents", {"query": query})


@mcp.tool()
def send_email(to: str, subject: str, attachment_name: str = "") -> dict:
    """Simulate an email request; no email is ever delivered by this tool."""
    return _guard("send_email", {"to": to, "subject": subject, "attachment": attachment_name}, provenance="unknown")


if __name__ == "__main__":
    mcp.run()
