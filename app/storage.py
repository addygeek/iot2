"""
Storage module - Manages sessions and file operations
"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from app.config import SESSIONS_DIR


class SessionStorage:
    """Manages session data and file storage"""
    
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
    
    def create_session(self, session_id: str) -> Path:
        """Create a new session directory"""
        session_dir = SESSIONS_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (session_dir / "chunks").mkdir(exist_ok=True)
        (session_dir / "converted").mkdir(exist_ok=True)
        
        # Initialize session metadata
        self.sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "chunks_received": 0,
            "transcript": "",
            "summary": "",
            "expected_seq": 0,
            "buffered_chunks": {},
            "last_summary_time": datetime.now().timestamp(),
            "word_count": 0
        }
        
        # Save metadata
        self._save_metadata(session_id)
        
        return session_dir
    
    def get_session_dir(self, session_id: str) -> Path:
        """Get session directory path"""
        return SESSIONS_DIR / session_id
    
    def save_chunk(self, session_id: str, seq: int, chunk_data: bytes, extension: str) -> Path:
        """Save audio chunk to disk"""
        chunk_path = self.get_session_dir(session_id) / "chunks" / f"chunk_{seq:05d}{extension}"
        chunk_path.write_bytes(chunk_data)
        
        # Update session metadata
        if session_id in self.sessions:
            self.sessions[session_id]["chunks_received"] += 1
        
        return chunk_path
    
    def get_converted_chunk_path(self, session_id: str, seq: int) -> Path:
        """Get path for converted WAV chunk"""
        return self.get_session_dir(session_id) / "converted" / f"chunk_{seq:05d}.wav"
    
    def update_transcript(self, session_id: str, text: str, append: bool = True):
        """Update session transcript"""
        if session_id not in self.sessions:
            return
        
        if append:
            self.sessions[session_id]["transcript"] += " " + text
        else:
            self.sessions[session_id]["transcript"] = text
        
        # Update word count
        self.sessions[session_id]["word_count"] = len(
            self.sessions[session_id]["transcript"].split()
        )
        
        # Save transcript to file
        transcript_path = self.get_session_dir(session_id) / "transcript.txt"
        transcript_path.write_text(self.sessions[session_id]["transcript"])
    
    def update_summary(self, session_id: str, summary: str):
        """Update session summary"""
        if session_id not in self.sessions:
            return
        
        self.sessions[session_id]["summary"] = summary
        self.sessions[session_id]["last_summary_time"] = datetime.now().timestamp()
        
        # Save summary to file
        summary_path = self.get_session_dir(session_id) / "summary.txt"
        summary_path.write_text(summary)
    
    def get_transcript(self, session_id: str) -> str:
        """Get current transcript"""
        return self.sessions.get(session_id, {}).get("transcript", "")
    
    def get_summary(self, session_id: str) -> str:
        """Get current summary"""
        return self.sessions.get(session_id, {}).get("summary", "")
    
    def get_session_metadata(self, session_id: str) -> dict:
        """Get session metadata"""
        return self.sessions.get(session_id, {})
    
    def should_generate_summary(self, session_id: str, word_threshold: int, time_interval: int) -> bool:
        """Check if summary should be generated"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # Check word count threshold
        if session["word_count"] >= word_threshold:
            return True
        
        # Check time interval
        time_since_last = datetime.now().timestamp() - session["last_summary_time"]
        if time_since_last >= time_interval and session["word_count"] > 50:
            return True
        
        return False
    
    def mark_session_ended(self, session_id: str):
        """Mark session as ended"""
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "ended"
            self.sessions[session_id]["ended_at"] = datetime.now().isoformat()
            self._save_metadata(session_id)
    
    def cleanup_session(self, session_id: str):
        """Remove session data"""
        session_dir = self.get_session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
        
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def list_sessions(self) -> List[dict]:
        """List all sessions"""
        return list(self.sessions.values())
    
    def _save_metadata(self, session_id: str):
        """Save session metadata to JSON file"""
        if session_id not in self.sessions:
            return
        
        metadata_path = self.get_session_dir(session_id) / "metadata.json"
        metadata_path.write_text(
            json.dumps(self.sessions[session_id], indent=2)
        )
    
    # Chunk ordering methods
    
    def get_expected_seq(self, session_id: str) -> int:
        """Get next expected sequence number"""
        return self.sessions.get(session_id, {}).get("expected_seq", 0)
    
    def increment_expected_seq(self, session_id: str):
        """Increment expected sequence number"""
        if session_id in self.sessions:
            self.sessions[session_id]["expected_seq"] += 1
    
    def buffer_future_chunk(self, session_id: str, seq: int, chunk_path: Path):
        """Buffer chunk that arrived out of order"""
        if session_id in self.sessions:
            self.sessions[session_id]["buffered_chunks"][seq] = str(chunk_path)
    
    def get_buffered_chunk(self, session_id: str, seq: int) -> Optional[Path]:
        """Get buffered chunk if available"""
        if session_id not in self.sessions:
            return None
        
        chunk_path = self.sessions[session_id]["buffered_chunks"].get(seq)
        if chunk_path:
            return Path(chunk_path)
        return None
    
    def remove_buffered_chunk(self, session_id: str, seq: int):
        """Remove chunk from buffer"""
        if session_id in self.sessions and seq in self.sessions[session_id]["buffered_chunks"]:
            del self.sessions[session_id]["buffered_chunks"][seq]


# Global storage instance
storage = SessionStorage()