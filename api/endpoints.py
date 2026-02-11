import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from core.rag import rag_manager
from core.graph import app_graph

router = APIRouter()
UPLOAD_DIR = "uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

class QueryRequest(BaseModel):
    query: str

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        chunks = rag_manager.process_file(file_path)
        return {"filename": file.filename, "chunks": len(chunks), "status": "processed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_docs(request: QueryRequest):
    try:
        inputs = {"query": request.query, "documents": [], "response": ""}
        result = app_graph.invoke(inputs)
        return {"response": result["response"], "sources": result.get("documents", [])[:3]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
