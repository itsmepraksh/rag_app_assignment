import os
from typing import List, TypedDict
from dotenv import load_dotenv
import google.generativeai as genai
from langgraph.graph import StateGraph, END
from core.rag import rag_manager

load_dotenv()
genai.configure(api_key=os.getenv("Gemini_API_Key"))

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
    You are an advanced AI assistant. Answer the user's question based ONLY on the provided context chunks.
    If the context doesn't contain the answer, say "I don't have enough information in the uploaded documents to answer this."
    
    CRITICAL INSTRUCTION: Your answer must be derived strictly from the Context below. Do not use outside knowledge.
    Use conversation history only to resolve references in follow-up questions (for example, "that section").
    Do not treat history as factual source; facts must come from context.
    {retry_instruction}

    Conversation History (last turns):
    {history_text}
    
    Context:
    {context}
    
    Question: {query}
    
    Answer:
    """
    
    model = genai.GenerativeModel("gemini-flash-latest")
    result = model.generate_content(prompt)
    return {
        "response": result.text,
        "generation_attempts": generation_attempts + 1,
    }

def quality_check_node(state: AgentState):
    print("--- QUALITY CHECK ---")
    response = (state.get("response") or "").strip()
    attempts = state.get("generation_attempts", 0)

    min_words = 25
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

    citation_text = "\n\n**Citations:**\n" + "\n".join([f"- {c}" for c in unique_citations])
    return {"response": state["response"] + citation_text, "citations": unique_citations}

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
