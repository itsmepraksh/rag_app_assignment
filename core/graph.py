import os
import logging
from typing import List, TypedDict
from langgraph.graph import StateGraph, END
from core.rag import rag_manager
from core.llm_client import generate

logger = logging.getLogger(__name__)

# State definition
class AgentState(TypedDict):
    query: str
    documents: List[dict]  # Updated to include metadata
    conversation_history: List[dict]
    response: str
    citations: List[str]
    iterations: int
    generation_attempts: int

# Nodes
def retriever_node(state: AgentState):
    print("--- RETRIEVING ---")
    query = state["query"]
    docs = rag_manager.query(query)
    logger.info("retrieval query=%r chunks=%d", query[:120], len(docs))
    # Store both content and metadata
    doc_data = [
        {
            "content": d.page_content,
            "metadata": d.metadata
        } for d in docs
    ]
    return {"documents": doc_data, "iterations": state.get("iterations", 0) + 1}

def validator_node(state: AgentState):
    print("--- VALIDATING ---")
    # Simple validation: if no docs found, maybe re-query or fail
    if not state["documents"]:
        return {"response": "I couldn't find any relevant information in the documents provided."}
    return state

def generator_node(state: AgentState):
    print("--- GENERATING ---")
    
    # Construct context with metadata
    context_parts = []
    
    for doc in state["documents"]:
        content = doc["content"]
        metadata = doc["metadata"]
        source = os.path.basename(metadata.get("source", "Unknown"))
        page = metadata.get("page", 0) + 1  # LangChain page index is 0-based
        
        context_parts.append(f"Source: {source} (Page {page})\nContent: {content}")
    
    context = "\n\n---\n\n".join(context_parts)
    context_word_count = len(context.split())
    context_density = "LOW" if context_word_count < 220 else "HIGH"
    query = state["query"]
    recent_history = state.get("conversation_history", [])[-3:]
    history_parts = []
    for i, turn in enumerate(recent_history, start=1):
        question = turn.get("question", "").strip()
        answer = turn.get("answer", "").strip()
        if question or answer:
            history_parts.append(f"Turn {i}\nQuestion: {question}\nAnswer: {answer}")
    history_text = "\n\n".join(history_parts) if history_parts else "No prior conversation."
    
    generation_attempts = state.get("generation_attempts", 0)
    retry_instruction = ""
    if generation_attempts > 0:
        retry_instruction = (
            "Previous answer was too short. Provide a fuller answer with clear detail, still using only context."
        )

    prompt = f"""
You are an advanced RAG assistant.

Instruction:
- Answer ONLY using the provided context.
- If context is insufficient, reply exactly:
  "I don't have enough information in the uploaded documents to answer this."
- Use conversation history only to resolve references in follow-up questions.
- Do not use outside knowledge.
- Give a direct answer only. No preface like "Based on the provided context".
- Do not include explanations about where the answer came from.
- Do not include citation text in the answer body.
- Keep output short and plain (1-3 lines).
- If user explicitly asks for detail (for example: "explain in detail", "step by step", "elaborate"), provide a longer response.
{retry_instruction}

Conversation History (last 3 turns):
{history_text}

Context Density:
{context_density}

Retrieved Context Chunks (with metadata):
{context}

User Question:
{query}

Final Answer:
"""

    try:
        response_text = ""
        for _ in range(2):  # retry once if empty response
            response_text = (generate(prompt) or "").strip()
            if response_text:
                break

        if not response_text:
            return {
                "response": (
                    "[GENERATOR_ERROR] "
                    "code=EMPTY_RESPONSE "
                    "message=LLM returned an empty response after retry."
                ),
                "generation_attempts": generation_attempts + 1,
            }

        return {
            "response": response_text,
            "generation_attempts": generation_attempts + 1,
        }
    except Exception as exc:
        return {
            "response": (
                "[GENERATOR_ERROR] "
                "code=LLM_EXCEPTION "
                f"message={str(exc)}"
            ),
            "generation_attempts": generation_attempts + 1,
        }

def quality_check_node(state: AgentState):
    print("--- QUALITY CHECK ---")
    response = (state.get("response") or "").strip()
    attempts = state.get("generation_attempts", 0)

    if response.startswith("[GENERATOR_ERROR]"):
        return {"regenerate": False}

    min_words = 8
    max_attempts = 2

    if len(response.split()) < min_words and attempts < max_attempts:
        return {"regenerate": True}
    return {"regenerate": False}

def citation_node(state: AgentState):
    print("--- APPENDING CITATIONS ---")
    citations = []

    for doc in state["documents"]:
        metadata = doc["metadata"]
        source = os.path.basename(metadata.get("source", "Unknown"))
        page = metadata.get("page", 0) + 1  # LangChain page index is 0-based
        citations.append(f"{source} (Page {page})")

    unique_citations = list(dict.fromkeys(citations))  # preserve order, remove duplicates
    if not unique_citations:
        return state
    return {"response": state["response"], "citations": unique_citations}

# Graph construction
workflow = StateGraph(AgentState)

workflow.add_node("retriever", retriever_node)
workflow.add_node("validator", validator_node)
workflow.add_node("generator", generator_node)
workflow.add_node("quality_check", quality_check_node)
workflow.add_node("citation", citation_node)

workflow.set_entry_point("retriever")
workflow.add_edge("retriever", "validator")

def decide_to_generate(state: AgentState):
    if "response" in state and state["response"]:
        return END
    return "generator"

workflow.add_conditional_edges(
    "validator",
    decide_to_generate,
    {
        "generator": "generator",
        END: END
    }
)

def decide_after_quality_check(state: AgentState):
    if state.get("regenerate"):
        return "generator"
    return "citation"

workflow.add_edge("generator", "quality_check")
workflow.add_conditional_edges(
    "quality_check",
    decide_after_quality_check,
    {
        "generator": "generator",
        "citation": "citation",
    }
)
workflow.add_edge("citation", END)

# Compile
app_graph = workflow.compile()
