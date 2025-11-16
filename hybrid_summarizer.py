"""
Hybrid Summarizer
-----------------
- MiniLM extractive summarizer (default)
- Optional T5-small abstractive summarizer (commented out)
- Loads models only ONCE when FastAPI boots
- Both models cached in RAM
"""

import threading
from transformers import AutoTokenizer, AutoModel, T5Tokenizer, T5ForConditionalGeneration
from summarizer import Summarizer

from app.config import SUMMARY_SENTENCE_COUNT


class HybridSummarizer:
    def __init__(self):
        # -----------------------------
        # LOAD DEFAULT MODEL (MiniLM)
        # -----------------------------
        print("🔄 Loading MiniLM summarizer (default)...")

        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.minilm_tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.minilm_model = AutoModel.from_pretrained(model_name)

        self.minilm_summarizer = Summarizer(
            custom_model=self.minilm_model,
            custom_tokenizer=self.minilm_tokenizer
        )

        self.use_t5 = False         # default off
        self.t5_loaded = False
        self.t5_model = None
        self.t5_tokenizer = None

        print("✓ MiniLM summarizer loaded")

        # lock for thread safety
        self.lock = threading.Lock()

    # ----------------------------------------------------
    # OPTIONAL — load T5 only once (heavy operation)
    # ----------------------------------------------------
    def enable_t5(self):
        """
        Enables abstractive summarization using T5-small.
        Loads once, keeps in RAM.
        """
        if self.t5_loaded:
            return

        print("⏳ Loading T5-small (abstractive summarizer)...")

        model_name = "t5-small"
        self.t5_tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.t5_model = T5ForConditionalGeneration.from_pretrained(model_name)

        self.t5_loaded = True
        self.use_t5 = True

        print("✓ T5-small loaded and ready")

    # ----------------------------------------------------
    # MiniLM EXTRACTIVE SUMMARY (fast)
    # ----------------------------------------------------
    def minilm_summary(self, text, ratio=0.15):
        if not text or len(text.strip()) < 50:
            return ""

        with self.lock:
            try:
                s = self.minilm_summarizer(text, ratio=ratio)
                return s.strip()
            except Exception as e:
                print("MiniLM summary error:", e)
                return text[:300]

    # ----------------------------------------------------
    # T5 ABSTRACTIVE SUMMARY (slow, 12–15 sec)
    # ----------------------------------------------------
    def t5_summary(self, text):
        if not self.t5_loaded:
            print("⚠️ T5 not loaded — using MiniLM instead")
            return self.minilm_summary(text)

        prep = "summarize: " + text.strip()

        with self.lock:
            try:
                inputs = self.t5_tokenizer.encode(prep, return_tensors="pt", max_length=1024, truncation=True)
                outputs = self.t5_model.generate(
                    inputs,
                    max_length=200,
                    min_length=40,
                    length_penalty=2.0,
                    num_beams=4,
                    early_stopping=True
                )
                summary = self.t5_tokenizer.decode(outputs[0], skip_special_tokens=True)
                return summary.strip()

            except Exception as e:
                print("T5 error:", e)
                return self.minilm_summary(text)

    # ----------------------------------------------------
    # MAIN ENTRYPOINT
    # ----------------------------------------------------
    def summarize(self, text):
        if self.use_t5:
            return self.t5_summary(text)
        return self.minilm_summary(text)


# GLOBAL SINGLETON INSTANCE (loaded once)
hybrid_summarizer = HybridSummarizer()

