"""Synthesize node — streams LLM response tokens and returns the full reply."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agents.events import EventPublisher
from app.agents.sanitizer import sanitize_user_content
from app.agents.state import AgentState
from app.core.config import settings

_NO_DOCS_REPLY = (
    "Zu dieser Frage habe ich keine passenden Inhalte in den hochgeladenen Dokumenten gefunden.\n\n"
    "Bitte stelle sicher, dass die relevanten Studienhefte hochgeladen und verarbeitet wurden "
    "(Status: *Bereit*). Du kannst die Frage auch umformulieren "
    "oder einen anderen Suchbegriff verwenden."
)


def _build_system_prompt(
    chunks: list[dict[str, Any]],
    memories: list[dict[str, Any]],
    web_results: list[dict[str, Any]] | None = None,
) -> str:
    has_web = bool(web_results)
    lines = [
        "You are Knowbase, a study assistant for distance-learning students.",
        "Respond in the same language the user used.",
        "",
        "You have TWO sources of information:",
        "  1. <retrieved_documents> — excerpts from the user's uploaded Studienhefte.",
        "  2. <web_results> — live web search results (supplementary only).",
        "",
        "══════════════════════════════════════════════",
        "STEP 1 — DETECT QUESTION TYPE",
        "══════════════════════════════════════════════",
        "",
        "ASSIGNMENT QUESTION (Einsendeaufgabe) signals — ANY of:",
        "  • Multiple numbered sub-questions (1. / 2. / 3. ...)",
        "  • Point values (Pkt., Punkte)",
        "  • Task verbs: Diskutieren, Analysieren, Bewerten, Beschreiben, Stellen Sie dar,",
        "    Setzen Sie sich auseinander, Wählen Sie aus, Erläutern Sie",
        "  • Personal-input phrases: 'aus Ihrer Erfahrung', 'aus Ihrem Alltag',",
        "    'eigene Beispiele', 'aus Ihrer Praxis', 'aus Ihrem Unternehmen',",
        "    'erfundenes Beispiel', 'Bekanntenkreis'",
        "",
        "If ASSIGNMENT QUESTION detected → apply ASSIGNMENT FORMAT (below).",
        "Otherwise → apply STANDARD FORMAT (below).",
        "",
        "══════════════════════════════════════════════",
        "STEP 2A — ASSIGNMENT FORMAT",
        "══════════════════════════════════════════════",
        "",
        "Structure your answer exactly as follows:",
        "",
        "For EACH numbered sub-question:",
        "  • Open with a bold heading: **Aufgabe [N]** (or the question's own title).",
        "  • Write in flowing prose (Fließtext) — NO bullet lists for the main answer.",
        "  • For every claim drawn from <retrieved_documents>: cite inline as",
        "    *(Quelle: SOURCE)* — copy SOURCE verbatim from the chunk's source= attribute.",
        "  • NEVER invent chapter names, headings, or page numbers.",
        "  • For sub-questions that ask for personal examples, use this two-part structure:",
        "",
        "    PART A — THEORETICAL FOUNDATION (from documents):",
        "    Write the conceptual content in prose with inline citations.",
        "",
        "    PART B — PERSONAL EXAMPLE SCAFFOLD:",
        "    After the theory, insert a clearly marked scaffold block:",
        "",
        "    > **[Ihr Praxisbeispiel]:** *Ergänzen Sie hier ein konkretes Beispiel aus",
        "    > Ihrer eigenen Berufspraxis, Ihrem Studium oder Ihrem Bekanntenkreis.",
        "    > Struktur: (1) Kontext / Situation beschreiben → (2) Bezug zum obigen",
        "    > Konzept [NAME DES KONZEPTS] herstellen → (3) Schlussfolgerung ziehen.*",
        "",
        "    Replace [NAME DES KONZEPTS] with the actual concept name from Part A.",
        "    If the task says 'erfundenes Beispiel ist erlaubt', note that explicitly.",
        "",
        "  • If <retrieved_documents> has NO relevant passage for a sub-topic:",
        "    Write: **Im bereitgestellten Material konnte hierzu keine eindeutige",
        "    Fundstelle gefunden werden.** Then still provide the scaffold if personal",
        "    examples are requested.",
        "",
        "  • Use <web_results> ONLY when documents have no passage. Mark with:",
        "    **Im bereitgestellten Material konnte hierzu keine eindeutige Fundstelle",
        "    gefunden werden.** Then cite as *(Quelle: Web – TITLE, URL)*.",
        "",
        "FORBIDDEN in assignment mode:",
        "  • Bullet lists for main content (use prose).",
        "  • Inventing or simulating personal examples.",
        "  • Using training-data knowledge to fill content gaps.",
        "  • A bibliography section at the end.",
        "",
        "══════════════════════════════════════════════",
        "STEP 2B — STANDARD FORMAT (non-assignment questions)",
        "══════════════════════════════════════════════",
        "",
        "PRIORITY 1 — STUDY MATERIAL (<retrieved_documents>):",
        "• For every sub-topic: first check whether a relevant passage exists.",
        "• If yes: answer strictly from that passage. Do NOT add training-data knowledge.",
        "• Citation: *(Quelle: SOURCE)* after every paragraph that draws from documents.",
        "• NEVER invent chapter names, headings, or page numbers.",
        "",
        "PRIORITY 2 — WEB RESULTS (<web_results>):",
        "• Use ONLY for sub-topics where <retrieved_documents> has no relevant passage.",
        "• Before using, write: **Im bereitgestellten Material konnte hierzu keine",
        "  eindeutige Fundstelle gefunden werden.**",
        "• Cite as: *(Quelle: Web – TITLE, URL)*",
        "",
        "PRIORITY 3 — NO SOURCE AT ALL:",
        "• Write: **Im bereitgestellten Material konnte hierzu keine eindeutige",
        "  Fundstelle gefunden werden.** Nothing else for that sub-topic.",
        "",
        "GENERAL RULES (both formats):",
        "• FORBIDDEN: training-data knowledge to fill any gap.",
        "• FORBIDDEN: presenting web content as study-material content.",
        "• FORBIDDEN: inventing or simulating personal examples.",
        "• No bibliography at the end.",
    ]

    if chunks:
        lines.append("\n<retrieved_documents>")
        for i, c in enumerate(chunks, 1):
            content = str(c.get("content", ""))[:2000]
            name = str(c.get("document_name", f"Document {i}"))
            chapter = str(c.get("chapter", "")).strip()
            doc_label = f"{name}, {chapter}" if chapter else name
            lines.append(f'<document id="{i}" source="{doc_label}">\n{content}\n</document>')
        lines.append("</retrieved_documents>")

    if web_results:
        lines.append("\n<web_results>")
        for i, r in enumerate(web_results, 1):
            title = str(r.get("title", f"Result {i}"))
            url = str(r.get("url", ""))
            content = str(r.get("content", ""))[:1000]
            lines.append(f'<result id="{i}" title="{title}" url="{url}">\n{content}\n</result>')
        lines.append("</web_results>")

    if memories:
        lines.append("\n<memories>")
        for m in memories:
            content = str(m.get("content", ""))[:500]
            scope = str(m.get("scope", ""))
            lines.append(f'<memory scope="{scope}">{content}</memory>')
        lines.append("</memories>")

    _ = has_web  # referenced in prompt text above
    return "\n".join(lines)


def _to_chat_messages(
    messages: list[BaseMessage],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            content = sanitize_user_content(
                m.content if isinstance(m.content, str) else str(m.content)
            )
            result.append({"role": "user", "content": content})
        elif isinstance(m, AIMessage):
            result.append({"role": "assistant", "content": str(m.content)})

    # Both Anthropic and OpenAI require alternating roles starting with user
    while result and result[0]["role"] == "assistant":
        result.pop(0)

    if not result:
        result.append({"role": "user", "content": "Please continue."})

    return result


async def _stream_anthropic(
    system_prompt: str,
    messages: list[dict[str, str]],
    publisher: EventPublisher,
) -> tuple[str, int, int]:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    full_text = ""
    input_tokens = 0
    output_tokens = 0

    async with client.messages.stream(
        model=settings.AGENT_MODEL,
        max_tokens=settings.AGENT_MAX_TOKENS,
        system=system_prompt,
        messages=messages,  # type: ignore[arg-type]
    ) as stream:
        async for text in stream.text_stream:
            full_text += text
            await publisher.token(text)
        final_msg = await stream.get_final_message()
        input_tokens = final_msg.usage.input_tokens
        output_tokens = final_msg.usage.output_tokens

    return full_text, input_tokens, output_tokens


async def _stream_openai(
    system_prompt: str,
    messages: list[dict[str, str]],
    publisher: EventPublisher,
) -> tuple[str, int, int]:
    import openai

    client = openai.AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE or None,
    )
    oai_messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        *messages,
    ]

    full_text = ""
    input_tokens = 0
    output_tokens = 0

    stream = await client.chat.completions.create(  # type: ignore[call-overload]
        model=settings.OPENAI_AGENT_MODEL,
        max_tokens=settings.AGENT_MAX_TOKENS,
        messages=oai_messages,
        stream=True,
        stream_options={"include_usage": True},
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            text = chunk.choices[0].delta.content
            full_text += text
            await publisher.token(text)
        if chunk.usage:
            input_tokens = chunk.usage.prompt_tokens
            output_tokens = chunk.usage.completion_tokens

    return full_text, input_tokens, output_tokens


async def synthesize_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    configurable = config.get("configurable", {})
    publisher: EventPublisher = configurable["publisher"]

    system_prompt = _build_system_prompt(
        state["retrieved_chunks"], state["memories"], state.get("web_results") or []
    )
    chat_messages = _to_chat_messages(state["messages"])

    await publisher.thinking(step="Generating response", agent="synthesize")

    if settings.ANTHROPIC_API_KEY:
        full_text, input_tokens, output_tokens = await _stream_anthropic(
            system_prompt, chat_messages, publisher
        )
    elif settings.OPENAI_API_KEY:
        full_text, input_tokens, output_tokens = await _stream_openai(
            system_prompt, chat_messages, publisher
        )
    else:
        placeholder = "*(No AI API key configured — set ANTHROPIC_API_KEY or OPENAI_API_KEY.)*"
        await publisher.token(placeholder)
        return {
            "messages": [AIMessage(content=placeholder)],
            "tokens_used": 0,
        }

    # Build a lookup from doc_label → chunk for chunks that have an id
    label_to_chunk: dict[str, dict[str, Any]] = {}
    for c in state["retrieved_chunks"]:
        if not c.get("document_id"):
            continue
        name = str(c.get("document_name", ""))
        chapter = str(c.get("chapter", "")).strip()
        label = f"{name}, {chapter}" if chapter else name
        label_to_chunk[label] = c

    # Parse *(Quelle: ...)* patterns from the actual response to find cited sources
    cited_labels: list[str] = []
    for m in re.finditer(r"\*\(Quelle:\s*([^)]+)\)\*", full_text):
        for part in m.group(1).split(";"):
            cited_labels.append(part.strip())

    # Emit only sources that were actually cited; fall back to all retrieved if none matched
    seen_ids: set[str] = set()
    source_docs: list[dict[str, str]] = []
    for label in cited_labels:
        chunk = label_to_chunk.get(label)
        if chunk is None:
            # Try prefix match (LLM may have slightly trimmed the label)
            for lbl, c in label_to_chunk.items():
                if lbl.startswith(label) or label.startswith(lbl):
                    chunk = c
                    break
        if chunk is None:
            continue
        doc_id = str(chunk.get("document_id", ""))
        chapter = str(chunk.get("chapter", "")).strip()
        key = f"{doc_id}:{chapter}"
        if key not in seen_ids:
            seen_ids.add(key)
            source_docs.append(
                {
                    "document_id": doc_id,
                    "document_name": str(chunk.get("document_name", "Unknown")),
                    "chapter": chapter,
                }
            )

    if not source_docs:
        # Fallback: emit all retrieved chunks when the LLM cited nothing parseable
        seen_ids2: set[tuple[str, str]] = set()
        for c in state["retrieved_chunks"]:
            doc_id = str(c.get("document_id", ""))
            if not doc_id:
                continue
            chapter = str(c.get("chapter", "")).strip()
            key2 = (doc_id, chapter)
            if key2 not in seen_ids2:
                seen_ids2.add(key2)
                source_docs.append(
                    {
                        "document_id": doc_id,
                        "document_name": str(c.get("document_name", "Unknown")),
                        "chapter": chapter,
                    }
                )

    if source_docs:
        await publisher.sources(source_docs)

    return {
        "messages": [AIMessage(content=full_text)],
        "tokens_used": state["tokens_used"] + input_tokens + output_tokens,
    }
