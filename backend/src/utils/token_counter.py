"""
Token counting utilities for Bedrock API calls.

Provides approximate token counting for monitoring costs and rate limits.
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TokenCounter:
    """Utility class for counting tokens in text."""
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count for text.
        
        Uses a simple approximation: ~4 characters per token for English text.
        This is close to OpenAI's tokenization and should be similar for Claude.
        
        Args:
            text: Input text to count tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Remove extra whitespace
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        
        # Rough approximation: 4 characters per token
        char_count = len(cleaned_text)
        estimated_tokens = max(1, char_count // 4)
        
        return estimated_tokens
    
    @staticmethod
    def estimate_tokens_detailed(text: str) -> Dict[str, int]:
        """
        Provide detailed token estimation breakdown.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dict with character count, word count, and estimated tokens
        """
        if not text:
            return {
                'characters': 0,
                'words': 0,
                'estimated_tokens': 0
            }
        
        # Clean text
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        
        # Count metrics
        char_count = len(cleaned_text)
        word_count = len(cleaned_text.split())
        estimated_tokens = max(1, char_count // 4)
        
        return {
            'characters': char_count,
            'words': word_count,
            'estimated_tokens': estimated_tokens
        }
    
    @staticmethod
    def log_token_usage(
        operation: str,
        input_text: str,
        output_text: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log token usage for an operation.
        
        Args:
            operation: Name of the operation (e.g., "bedrock_agent_call", "claude_invoke")
            input_text: Input text sent to the model
            output_text: Output text received from the model
            model_id: Model identifier
            
        Returns:
            Dict with token usage statistics
        """
        input_stats = TokenCounter.estimate_tokens_detailed(input_text)
        output_stats = TokenCounter.estimate_tokens_detailed(output_text or "")
        
        total_tokens = input_stats['estimated_tokens'] + output_stats['estimated_tokens']
        
        usage_stats = {
            'operation': operation,
            'model_id': model_id,
            'input_tokens': input_stats['estimated_tokens'],
            'output_tokens': output_stats['estimated_tokens'],
            'total_tokens': total_tokens,
            'input_characters': input_stats['characters'],
            'output_characters': output_stats['characters'],
            'input_words': input_stats['words'],
            'output_words': output_stats['words']
        }
        
        # Log the usage
        logger.info(
            f"🔢 Token Usage - {operation}: "
            f"Input: {input_stats['estimated_tokens']} tokens "
            f"({input_stats['characters']} chars, {input_stats['words']} words) | "
            f"Output: {output_stats['estimated_tokens']} tokens "
            f"({output_stats['characters']} chars, {output_stats['words']} words) | "
            f"Total: {total_tokens} tokens"
        )
        
        # Warn if usage is high
        if total_tokens > 8000:
            logger.warning(f"⚠️  High token usage detected: {total_tokens} tokens for {operation}")
        elif total_tokens > 4000:
            logger.info(f"📊 Moderate token usage: {total_tokens} tokens for {operation}")
        
        return usage_stats


# Global token counter instance
token_counter = TokenCounter()