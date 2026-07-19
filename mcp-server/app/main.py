"""Knowbase MCP server — stdio transport, three tools.

Tools:
  search_knowledge(query, k=8)   semantic search over workspace documents
  list_documents()                list all ready documents in the workspace
  get_document(document_id)       metadata for a specific document

Auth: set KNOWBASE_API_KEY to a `kb_<hex>` personal access token issued by
the Knowbase API (/auth/api-keys). The workspace is determined by the key itself —
there is no workspace ID to configure here.

Run:
  knowbase-mcp            (via project.scripts entry point)
  python -m app.main      (direct)
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.client import KnowbaseClient
from app.config import Settings

mcp: FastMCP = FastMCP("Knowbase")

# Module-level client — overrideable by tests via `import app.main; app.main._client = ...`
_client: KnowbaseClient | None = None


def _get_client() -> KnowbaseClient:
    global _client
    if _client is None:
        _client = KnowbaseClient(Settings())  # type: ignore[call-arg]
    return _client


@mcp.tool()
async def search_knowledge(query: str, k: int = 8) -> str:
    """Search the Knowbase workspace for information relevant to *query*.

    Returns the top-k most relevant document chunks ranked by cosine distance.
    Each result includes the source label (document name + chapter) so the
    calling agent can construct accurate citations.

    Args:
        query: Natural-language search query.
        k: Number of chunks to return (1-20, default 8).
    """
    chunks = await _get_client().search(query, k)
    if not chunks:
        return "No relevant information found for this query."

    lines: list[str] = [f"Found {len(chunks)} relevant chunk(s):\n"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"[{i}] {chunk['source_label']}  (distance: {chunk['distance']})")
        lines.append(chunk["content"])
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
async def list_documents() -> str:
    """List all ready documents available in the Knowbase workspace.

    Returns document names and IDs. Use the ID with get_document() for metadata
    or with search_knowledge() to narrow a search to a known document.
    """
    docs = await _get_client().list_documents()
    if not docs:
        return "No documents found in the workspace."

    lines: list[str] = [f"{len(docs)} document(s) in workspace:\n"]
    for doc in docs:
        lines.append(f"  {doc['name']}  (id: {doc['id']})")
    return "\n".join(lines)


@mcp.tool()
async def get_document(document_id: str) -> str:
    """Get metadata for a specific document.

    Args:
        document_id: UUID of the document (from list_documents).
    """
    doc = await _get_client().get_document(document_id)
    mime = doc.get("mime_type") or "unknown"
    return (
        f"Name:      {doc['name']}\n"
        f"ID:        {doc['id']}\n"
        f"Status:    {doc['status']}\n"
        f"MIME type: {mime}\n"
    )


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
