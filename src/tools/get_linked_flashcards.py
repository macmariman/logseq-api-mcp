"""Get flashcards from a Logseq page and all its linked pages."""

from typing import Any, List
from mcp.types import TextContent

from src.client.logseq_client import LogseqClient
from src.client.config import load_config


def _extract_flashcard_question(content: str) -> str:
    """Extract the question text from a flashcard block's content.

    Args:
        content: Raw block content containing #card marker.

    Returns:
        Cleaned question string with options if present.

    Complexity: O(L) where L is line count.
    """
    clean = content.replace("#card", "").strip()
    lines = clean.split("\n")
    if not lines:
        return clean

    question = lines[0].strip()
    options = [
        line.strip()
        for line in lines[1:]
        if line.strip() and line.strip().startswith(("+ [", "- [", "  + [", "  - ["))
    ]
    return question + "\n" + "\n".join(options) if options else question


def _find_flashcards_in_blocks(blocks: list[dict], page_info: dict) -> list[dict]:
    """Recursively find flashcard blocks in a block tree.

    Args:
        blocks: List of block dicts with optional 'children'.
        page_info: Page metadata dict to attach to each flashcard.

    Returns:
        List of flashcard dicts with content, properties, children, and page info.

    Complexity: O(N) where N is total block count.
    """
    flashcards: list[dict] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        content = block.get("content", "")
        if "#card" in content:
            flashcards.append({
                "block_id": block.get("id"),
                "block_uuid": block.get("uuid"),
                "content": content,
                "properties": block.get("properties", {}),
                "children": block.get("children", []),
                "page": page_info,
            })
        children = block.get("children", [])
        if children:
            flashcards.extend(_find_flashcards_in_blocks(children, page_info))
    return flashcards


async def _run(client: LogseqClient, page_identifier: str) -> List[TextContent]:
    """Find and format flashcards from a page and its links using an injected client.

    Args:
        client: LogseqClient instance.
        page_identifier: The name or UUID of the target page.

    Returns:
        List with one TextContent containing the flashcard analysis.

    Complexity: O(P * B) where P is page count, B is average block count.
    """
    try:
        linked_refs = await client.get_page_linked_references(page_identifier)
        all_pages = await client.get_all_pages()

        page_lookup: dict[Any, dict] = {}
        for page in all_pages:
            if not isinstance(page, dict):
                continue
            p_id = page.get("id")
            p_name = (page.get("name") or "").lower()
            p_orig = (page.get("originalName") or "").lower()
            if p_id:
                page_lookup[p_id] = page
            if p_name:
                page_lookup[p_name] = page
            if p_orig:
                page_lookup[p_orig] = page

        target_page = page_lookup.get(page_identifier.lower())
        if not target_page:
            return [TextContent(type="text", text=f"❌ Target page '{page_identifier}' not found")]

        pages_to_search: list[dict] = [target_page]
        for group in linked_refs:
            if not isinstance(group, list) or len(group) < 1:
                continue
            ref = group[0]
            if not isinstance(ref, dict):
                continue
            ref_id = ref.get("id")
            if ref_id and ref_id in page_lookup:
                pages_to_search.append(page_lookup[ref_id])

        all_flashcards: list[dict] = []
        for page in pages_to_search:
            page_name_key = page.get("name") or page.get("id")
            blocks = await client.get_page_blocks_tree(page_name_key)
            if blocks:
                all_flashcards.extend(_find_flashcards_in_blocks(blocks, page))

        if not all_flashcards:
            return [TextContent(
                type="text",
                text=f"✅ No flashcards found in '{page_identifier}' or its linked pages",
            )]

        enriched: list[dict] = []
        for fc in all_flashcards:
            question = _extract_flashcard_question(fc["content"])
            answers: list[dict] = []
            for child in fc.get("children", []):
                if isinstance(child, dict):
                    child_block = await client.get_block(child.get("uuid", ""))
                    if child_block:
                        answer_content = child_block.get("content", "").strip()
                        if answer_content:
                            answers.append({
                                "content": answer_content,
                                "block_id": child_block.get("id"),
                                "block_uuid": child_block.get("uuid"),
                            })
            enriched.append({
                "question": question,
                "answers": answers,
                "properties": fc["properties"],
                "block_id": fc["block_id"],
                "block_uuid": fc["block_uuid"],
                "page": {
                    "name": fc["page"].get("originalName") or fc["page"].get("name"),
                    "id": fc["page"].get("id"),
                    "uuid": fc["page"].get("uuid"),
                },
            })

        enriched.sort(key=lambda f: (f["page"]["name"] or "", f["block_id"] or 0))

        target_name = target_page.get("originalName") or target_page.get("name")
        lines = [
            "🎯 **LINKED FLASHCARDS ANALYSIS**",
            f"📄 Target Page: {target_name}",
            f"🔗 Searched {len(pages_to_search)} pages (target + {len(pages_to_search) - 1} linked)",
            f"💡 Found {len(enriched)} flashcards total",
            "",
            "🧠 **FLASHCARDS:**",
            "",
        ]

        # Group by page
        by_page: dict[str, list[dict]] = {}
        for fc in enriched:
            by_page.setdefault(fc["page"]["name"] or "", []).append(fc)

        for p_name, fcs in by_page.items():
            lines.extend([f"📚 **{p_name}** ({len(fcs)} flashcards)", ""])
            for i, fc in enumerate(fcs, 1):
                lines.extend([
                    f"💡 **Flashcard {i}**",
                    f"   🔑 Block ID: {fc['block_id']} | UUID: {fc['block_uuid']}",
                    f"   📄 Page: {fc['page']['name']} (ID: {fc['page']['id']})",
                    "",
                    f"   ❓ **QUESTION:**",
                    f"   {fc['question']}",
                    "",
                ])
                if fc["answers"]:
                    lines.append("   💡 **ANSWERS:**")
                    for j, ans in enumerate(fc["answers"], 1):
                        lines.extend([
                            f"   {j}. {ans['content']}",
                            f"      └─ Block ID: {ans['block_id']} | UUID: {ans['block_uuid']}",
                        ])
                else:
                    lines.append("   💡 **ANSWERS:** No answer blocks found")
                lines.append("")

        total_answers = sum(len(fc["answers"]) for fc in enriched)
        lines.extend([
            "📊 **SUMMARY:**",
            f"• Total flashcards: {len(enriched)}",
            f"• Total answer blocks: {total_answers}",
            f"• Pages with flashcards: {len(by_page)}",
        ])

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as exc:
        return [TextContent(type="text", text=f"❌ Error fetching linked flashcards: {exc}")]


async def get_linked_flashcards(page_identifier: str) -> List[TextContent]:
    """Get flashcards from the specified page and all pages that link to it.

    Args:
        page_identifier: The name or UUID of the page to search flashcards from.

    Returns:
        List with one TextContent containing the flashcard analysis.

    Complexity: O(P * B) where P is page count, B is average block count.
    """
    return await _run(LogseqClient(load_config()), page_identifier)
