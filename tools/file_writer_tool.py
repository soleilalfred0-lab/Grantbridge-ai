"""
tools/file_writer_tool.py

LangGraph-compatible Proposal File Writer Tool.
Saves generated grant proposals to disk and returns a download path.
"""

import os
import re
import uuid
import logging
from datetime import datetime
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

PROPOSALS_DIR = os.getenv("PROPOSALS_DIR", "./data/proposals")


@tool
def write_proposal_file(
    proposal_text: str,
    business_name: str,
    grant_name: str,
    language: str = "English",
) -> str:
    """
    Save a grant proposal draft to a file and return the download path.

    Use this tool after generating a proposal draft to persist it as a
    downloadable file. The file is saved in Markdown format with a clean
    filename derived from the business and grant names.

    Args:
        proposal_text:  The full proposal text to save.
        business_name:  Name of the entrepreneur's business.
        grant_name:     Name of the grant being applied for.
        language:       Language the proposal is written in.

    Returns:
        JSON string with:
          - file_path: relative path to the saved file
          - download_url: URL path to download the file
          - filename: the file's name
          - word_count: number of words in the proposal
          - created_at: timestamp
    """
    import json

    try:
        os.makedirs(PROPOSALS_DIR, exist_ok=True)

        # Build a clean filename
        safe_business = _slugify(business_name)
        safe_grant    = _slugify(grant_name)
        timestamp     = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        uid           = uuid.uuid4().hex[:6]
        filename      = f"{safe_business}__{safe_grant}__{timestamp}_{uid}.md"
        filepath      = os.path.join(PROPOSALS_DIR, filename)

        # Build the file content with a header
        header = _build_header(business_name, grant_name, language)
        full_content = header + "\n\n" + proposal_text

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)

        word_count = len(proposal_text.split())
        download_url = f"/api/proposals/download/{filename}"

        logger.info(f"write_proposal_file: saved '{filename}' ({word_count} words)")

        return json.dumps({
            "success": True,
            "file_path": filepath,
            "download_url": download_url,
            "filename": filename,
            "word_count": word_count,
            "created_at": datetime.utcnow().isoformat() + "Z",
        })

    except Exception as e:
        logger.error(f"write_proposal_file error: {e}")
        return json.dumps({"success": False, "error": str(e)})


def _slugify(text: str) -> str:
    """Convert text to a safe filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:40]


def _build_header(business_name: str, grant_name: str, language: str) -> str:
    now = datetime.utcnow().strftime("%B %d, %Y")
    return f"""# Grant Proposal Draft
**Business:** {business_name}
**Grant:** {grant_name}
**Language:** {language}
**Generated:** {now}
**Powered by:** GrantBridge AI

---
"""
