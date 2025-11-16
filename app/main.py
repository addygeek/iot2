"""
Main FastAPI application
Unified server for chunk upload + WebSocket broadcasting
"""
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import List
from pathlib import Path
from app.config import HOST, PORT, MAX_CHUNK_SIZE, SUPPORTED_FORMATS
from app.storage import storage
from app.workers import processor


# WebSocket Manager
class WebSocketManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"  ✓ WebSocket client connected ({len(self.active_connections)} total)")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"  ✗ WebSocket client disconnected ({len(self.active_connections)} remaining)")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        json_message = json.dumps(message)
        
        # Send to all clients
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json_message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Initialize FastAPI app
app = FastAPI(
    title="Meeting Recorder API",
    description="Real-time audio transcription and summarization",
    version="2.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize WebSocket manager
ws_manager = WebSocketManager()

# Connect processor to WebSocket manager
processor.set_websocket_manager(ws_manager)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API status"""
    return {
        "status": "running",
        "service": "Meeting Recorder API",
        "version": "2.0",
        "endpoints": {
            "create_session": "POST /session/create",
            "upload_chunk": "POST /session/{session_id}/upload",
            "end_session": "POST /session/{session_id}/end",
            "get_transcript": "GET /session/{session_id}/transcript",
            "get_summary": "GET /session/{session_id}/summary",
            "websocket": "WS /ws"
        }
    }


@app.post("/session/create")
async def create_session(session_id: str = Form(...)):
    """
    Create a new recording session
    
    Args:
        session_id: Unique session identifier
    
    Returns:
        Session metadata
    """
    try:
        storage.create_session(session_id)
        
        return JSONResponse({
            "status": "created",
            "session_id": session_id,
            "message": f"Session {session_id} created successfully"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/upload")
async def upload_chunk(
    session_id: str,
    seq: int = Form(...),
    timestamp: float = Form(...),
    chunk: UploadFile = File(...)
):
    """
    Upload audio chunk
    
    Args:
        session_id: Session identifier
        seq: Sequence number (0, 1, 2, ...)
        timestamp: Client timestamp
        chunk: Audio file (webm, ogg, wav, mp3, m4a)
    
    Returns:
        Upload confirmation
    """
    try:
        # Validate chunk size
        chunk_data = await chunk.read()
        if len(chunk_data) > MAX_CHUNK_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Chunk size exceeds {MAX_CHUNK_SIZE} bytes"
            )
        
        # Validate file extension
        extension = Path(chunk.filename).suffix.lower()
        if extension not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format. Allowed: {SUPPORTED_FORMATS}"
            )
        
        # Save chunk
        chunk_path = storage.save_chunk(session_id, seq, chunk_data, extension)
        
        # Process chunk asynchronously
        asyncio.create_task(processor.process_chunk(session_id, seq, chunk_path))
        
        return JSONResponse({
            "status": "received",
            "session_id": session_id,
            "seq": seq,
            "size": len(chunk_data)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/end")
async def end_session(session_id: str):
    """
    End recording session and generate final summary
    
    Args:
        session_id: Session identifier
    
    Returns:
        Final session data
    """
    try:
        # Finalize session (generates final summary)
        await processor.finalize_session(session_id)
        
        # Get final data
        transcript = storage.get_transcript(session_id)
        summary = storage.get_summary(session_id)
        metadata = storage.get_session_metadata(session_id)
        
        return JSONResponse({
            "status": "ended",
            "session_id": session_id,
            "transcript": transcript,
            "summary": summary,
            "metadata": metadata
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}/transcript")
async def get_transcript(session_id: str):
    """Get current transcript"""
    transcript = storage.get_transcript(session_id)
    
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    return JSONResponse({
        "session_id": session_id,
        "transcript": transcript
    })


@app.get("/session/{session_id}/summary")
async def get_summary(session_id: str):
    """Get current summary"""
    summary = storage.get_summary(session_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not available yet")
    
    return JSONResponse({
        "session_id": session_id,
        "summary": summary
    })


@app.get("/session/{session_id}/download/transcript")
async def download_transcript(session_id: str):
    """Download transcript as text file"""
    transcript_path = storage.get_session_dir(session_id) / "transcript.txt"
    
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    return FileResponse(
        path=transcript_path,
        filename=f"{session_id}_transcript.txt",
        media_type="text/plain"
    )


@app.get("/session/{session_id}/download/summary")
async def download_summary(session_id: str):
    """Download summary as text file"""
    summary_path = storage.get_session_dir(session_id) / "summary.txt"
    
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="Summary not found")
    
    return FileResponse(
        path=summary_path,
        filename=f"{session_id}_summary.txt",
        media_type="text/plain"
    )


@app.get("/sessions")
async def list_sessions():
    """List all sessions"""
    sessions = storage.list_sessions()
    return JSONResponse({"sessions": sessions})


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete session data"""
    try:
        storage.cleanup_session(session_id)
        return JSONResponse({
            "status": "deleted",
            "session_id": session_id
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    
    Clients receive:
    - transcript_update: New transcribed text
    - summary: Generated summary
    - session_ended: Session finalization
    """
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            
            # Optional: handle client messages
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except:
                pass
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("\n" + "="*70)
    print("  MEETING RECORDER API - PRODUCTION READY")
    print("="*70)
    print(f"\n  📡 Server: http://{HOST}:{PORT}")
    print(f"  🔌 WebSocket: ws://{HOST}:{PORT}/ws")
    print(f"  📝 API Docs: http://{HOST}:{PORT}/docs")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info"
    )