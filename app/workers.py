"""
Workers module - Async chunk processing with ordering
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from app.config import VOSK_SAMPLE_RATE
from app.storage import storage
from app.transcriber import transcriber
from app.summarizer import summarizer
from app.config import SUMMARY_WORD_THRESHOLD, SUMMARY_TIME_INTERVAL


class ChunkProcessor:
    """Handles async chunk processing with ordering"""
    
    def __init__(self):
        self.processing_tasks = {}
        self.websocket_manager = None  # Set by main.py
    
    def set_websocket_manager(self, manager):
        """Set WebSocket manager for broadcasting"""
        self.websocket_manager = manager
    
    async def process_chunk(self, session_id: str, seq: int, chunk_path: Path):
        """
        Process a single chunk: convert -> transcribe -> update
        
        Handles chunk ordering:
        - If seq matches expected: process immediately
        - If seq < expected: ignore (duplicate)
        - If seq > expected: buffer for later
        """
        try:
            expected_seq = storage.get_expected_seq(session_id)
            
            # Case 1: Duplicate chunk (already processed)
            if seq < expected_seq:
                print(f"  ⚠ Ignoring duplicate chunk {seq} (expected {expected_seq})")
                return
            
            # Case 2: Out-of-order chunk (future)
            if seq > expected_seq:
                print(f"  ⏳ Buffering future chunk {seq} (expected {expected_seq})")
                storage.buffer_future_chunk(session_id, seq, chunk_path)
                return
            
            # Case 3: Expected chunk - process it!
            print(f"  ✓ Processing chunk {seq}")
            
            # Step 1: Convert to WAV
            wav_path = await self._convert_to_wav(session_id, seq, chunk_path)
            if not wav_path:
                print(f"  ✗ Conversion failed for chunk {seq}")
                return
            
            # Step 2: Transcribe
            text = transcriber.transcribe_chunk(session_id, wav_path)
            
            if text:
                # Update transcript
                storage.update_transcript(session_id, text, append=True)
                
                # Broadcast transcript update
                await self._broadcast_transcript_update(session_id, text)
                
                # Check if summary should be generated
                if storage.should_generate_summary(
                    session_id, 
                    SUMMARY_WORD_THRESHOLD, 
                    SUMMARY_TIME_INTERVAL
                ):
                    await self._generate_and_broadcast_summary(session_id)
            
            # Increment expected sequence
            storage.increment_expected_seq(session_id)
            
            # Process any buffered future chunks that are now ready
            await self._process_buffered_chunks(session_id)
            
        except Exception as e:
            print(f"✗ Error processing chunk {seq}: {e}")
    
    async def _convert_to_wav(self, session_id: str, seq: int, input_path: Path) -> Optional[Path]:
        """
        Convert audio chunk to 16kHz mono WAV using ffmpeg
        
        This is CRITICAL for Vosk compatibility
        """
        try:
            output_path = storage.get_converted_chunk_path(session_id, seq)
            
            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-i', str(input_path),  # Input file
                '-ar', str(VOSK_SAMPLE_RATE),  # 16kHz sample rate
                '-ac', '1',  # Mono
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                str(output_path)  # Output file
            ]
            
            # Run conversion
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and output_path.exists():
                return output_path
            else:
                print(f"  ✗ ffmpeg error: {stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"  ✗ Conversion error: {e}")
            return None
    
    async def _process_buffered_chunks(self, session_id: str):
        """Process any buffered chunks that are now ready"""
        while True:
            expected_seq = storage.get_expected_seq(session_id)
            buffered_chunk = storage.get_buffered_chunk(session_id, expected_seq)
            
            if not buffered_chunk:
                break
            
            print(f"  ♻ Processing buffered chunk {expected_seq}")
            storage.remove_buffered_chunk(session_id, expected_seq)
            
            # Process the buffered chunk
            await self.process_chunk(session_id, expected_seq, buffered_chunk)
    
    async def _generate_and_broadcast_summary(self, session_id: str):
        """Generate summary and broadcast to clients"""
        try:
            # Get current transcript
            transcript = storage.get_transcript(session_id)
            
            if not transcript or len(transcript.split()) < 30:
                return
            
            # Generate summary
            print(f"\n  🔄 Generating summary for {session_id}...")
            summary = summarizer.summarize(transcript)
            
            if summary:
                # Store summary
                storage.update_summary(session_id, summary)
                
                # Broadcast to clients
                await self._broadcast_summary(session_id, summary)
                
        except Exception as e:
            print(f"✗ Summary generation error: {e}")
    
    async def _broadcast_transcript_update(self, session_id: str, text: str):
        """Broadcast transcript update via WebSocket"""
        if self.websocket_manager:
            message = {
                "type": "transcript_update",
                "session_id": session_id,
                "text": text,
                "full_transcript": storage.get_transcript(session_id)
            }
            await self.websocket_manager.broadcast(message)
    
    async def _broadcast_summary(self, session_id: str, summary: str):
        """Broadcast summary via WebSocket"""
        if self.websocket_manager:
            message = {
                "type": "summary",
                "session_id": session_id,
                "summary": summary
            }
            await self.websocket_manager.broadcast(message)
    
    async def finalize_session(self, session_id: str):
        """Generate final summary when session ends"""
        try:
            print(f"\n  🏁 Finalizing session {session_id}...")
            
            # Get final text from recognizer
            final_text = transcriber.finalize_session(session_id)
            if final_text:
                storage.update_transcript(session_id, final_text, append=True)
            
            # Generate final summary
            transcript = storage.get_transcript(session_id)
            if transcript and len(transcript.split()) >= 10:
                summary = summarizer.summarize(transcript)
                storage.update_summary(session_id, summary)
                
                # Broadcast final summary
                await self._broadcast_summary(session_id, summary)
            
            # Mark as ended
            storage.mark_session_ended(session_id)
            
            # Broadcast session ended
            if self.websocket_manager:
                message = {
                    "type": "session_ended",
                    "session_id": session_id,
                    "transcript": storage.get_transcript(session_id),
                    "summary": storage.get_summary(session_id)
                }
                await self.websocket_manager.broadcast(message)
            
        except Exception as e:
            print(f"✗ Error finalizing session: {e}")


# Global processor instance
processor = ChunkProcessor()