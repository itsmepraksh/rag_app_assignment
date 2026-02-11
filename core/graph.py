from typing import List, TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from core.rag import rag_manager

# State definition
class AgentState(TypedDict):
    query: str
    documents: List[str]
    response: str
    iterations: int

# Nodes
def retriever_node(state: AgentState):
    print("--- RETRIEVING ---")
    query = state["query"]
    docs = rag_manager.query(query)
    doc_texts = [d.page_content for d in docs]
    return {"documents": doc_texts, "iterations": state.get("iterations", 0) + 1}

def validator_node(state: AgentState):
    print("--- VALIDATING ---")
    # Simple validation: if no docs found, maybe re-query or fail
    if not state["documents"]:
        return {"response": "I couldn't find any relevant information in the documents provided."}
    return state

def generator_node(state: AgentState):
    print("--- GENERATING ---")
    # In a real setup, we'd call a local LLM (e.g., Ollama)
    # For now, we'll simulate a response or use a simple heuristic
    # if no LLM is configured.
    context = "\n".join(state["documents"])
    query = state["query"]
    
    # Placeholder for LLM call
    response = f"Based on the context: {context[:200]}... \n\nI found that: [Simulated Response for '{query}']"
    return {"response": response}

# Graph construction
workflow = StateGraph(AgentState)

workflow.add_node("retriever", retriever_node)
workflow.add_node("validator", validator_node)
workflow.add_node("generator", generator_node)

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

workflow.add_edge("generator", END)

# Compile
app_graph = workflow.compile()
