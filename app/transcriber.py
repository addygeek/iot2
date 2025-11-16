"""
Transcriber module - Vosk-based speech-to-text
"""
import json
import wave
from pathlib import Path
from typing import Optional
from vosk import Model, KaldiRecognizer
from app.config import VOSK_MODEL_PATH, VOSK_SAMPLE_RATE


class VoskTranscriber:
    """Vosk-based speech-to-text transcriber"""
    
    def __init__(self):
        self.model = None
        self.recognizers = {}  # Session-specific recognizers
        self._load_model()
    
    def _load_model(self):
        """Load Vosk model"""
        if not VOSK_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Vosk model not found at {VOSK_MODEL_PATH}\n"
                f"Please download vosk-model-en-in-0.5 and extract to models/"
            )
        
        print(f"Loading Vosk model from: {VOSK_MODEL_PATH}")
        try:
            self.model = Model(str(VOSK_MODEL_PATH))
            print("✓ Vosk model loaded successfully")
        except Exception as e:
            print(f"✗ Error loading Vosk model: {e}")
            raise
    
    def get_recognizer(self, session_id: str) -> KaldiRecognizer:
        """Get or create recognizer for session"""
        if session_id not in self.recognizers:
            self.recognizers[session_id] = KaldiRecognizer(
                self.model,
                VOSK_SAMPLE_RATE
            )
        return self.recognizers[session_id]
    
    def transcribe_chunk(self, session_id: str, wav_path: Path) -> Optional[str]:
        """
        Transcribe audio chunk
        
        Args:
            session_id: Session identifier
            wav_path: Path to WAV file (must be 16kHz mono)
        
        Returns:
            Transcribed text or None
        """
        try:
            recognizer = self.get_recognizer(session_id)
            
            # Open WAV file
            with wave.open(str(wav_path), "rb") as wf:
                # Validate format
                if wf.getnchannels() != 1:
                    print(f"✗ Audio must be mono, got {wf.getnchannels()} channels")
                    return None
                
                if wf.getframerate() != VOSK_SAMPLE_RATE:
                    print(f"✗ Audio must be {VOSK_SAMPLE_RATE}Hz, got {wf.getframerate()}Hz")
                    return None
                
                # Process audio
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    recognizer.AcceptWaveform(data)
                
                # Get final result for this chunk
                result = json.loads(recognizer.FinalResult())
                text = result.get("text", "").strip()
                
                if text:
                    print(f"  [{session_id}] Transcribed: {text}")
                    return text
                
                return None
                
        except Exception as e:
            print(f"✗ Transcription error: {e}")
            return None
    
    def finalize_session(self, session_id: str) -> Optional[str]:
        """Get final result and cleanup recognizer"""
        if session_id in self.recognizers:
            recognizer = self.recognizers[session_id]
            result = json.loads(recognizer.FinalResult())
            text = result.get("text", "").strip()
            
            # Cleanup
            del self.recognizers[session_id]
            
            return text if text else None
        
        return None
    
    def cleanup_recognizer(self, session_id: str):
        """Remove recognizer for session"""
        if session_id in self.recognizers:
            del self.recognizers[session_id]


# Global transcriber instance
transcriber = VoskTranscriber()