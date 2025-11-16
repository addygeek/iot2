"""
Summarizer module - LexRank-based extractive summarization
Optimized for Raspberry Pi 5 (4GB RAM)
"""
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
from app.config import SUMMARY_SENTENCE_COUNT


class TextSummarizer:
    """
    LexRank-based extractive summarizer
    Fast, lightweight, perfect for Pi
    """
    
    def __init__(self, language: str = "english"):
        self.language = language
        self.stemmer = Stemmer(language)
        self.summarizer = LexRankSummarizer(self.stemmer)
        self.summarizer.stop_words = get_stop_words(language)
        
        print("✓ LexRank summarizer initialized")
    
    def summarize(self, text: str, sentence_count: int = SUMMARY_SENTENCE_COUNT) -> str:
        """
        Generate extractive summary
        
        Args:
            text: Input text to summarize
            sentence_count: Number of sentences in summary
        
        Returns:
            Summary text
        """
        if not text or len(text.strip()) < 50:
            return ""
        
        try:
            # Parse text
            parser = PlaintextParser.from_string(text, Tokenizer(self.language))
            
            # Generate summary
            summary_sentences = self.summarizer(parser.document, sentence_count)
            
            # Convert to text
            summary = " ".join(str(sentence) for sentence in summary_sentences)
            
            if summary:
                print(f"  📝 Summary generated: {len(summary)} chars")
            
            return summary
            
        except Exception as e:
            print(f"✗ Summarization error: {e}")
            # Fallback: return first N sentences
            return self._fallback_summary(text, sentence_count)
    
    def _fallback_summary(self, text: str, sentence_count: int) -> str:
        """
        Fallback method: simple sentence extraction
        """
        sentences = text.split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Take first N sentences
        selected = sentences[:sentence_count]
        return '. '.join(selected) + '.'
    
    def quick_summary(self, text: str) -> str:
        """
        Generate a quick one-sentence summary
        Useful for real-time updates
        """
        return self.summarize(text, sentence_count=1)


# Global summarizer instance
summarizer = TextSummarizer()