import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("metrics_logger")

class MetricsLogger:
    @staticmethod
    def log_section_generation(
        session_id: str, 
        section_id: str, 
        provider: str, 
        model: str, 
        tokens_used: int, 
        duration_sec: float, 
        retries: int = 0
    ):
        """Log metrics for a single report section's generation."""
        logger.info(
            f"[METRIC] section_generated | session={session_id} | section={section_id} | "
            f"provider={provider} | model={model} | tokens={tokens_used} | "
            f"duration={duration_sec:.2f}s | retries={retries}"
        )

    @staticmethod
    def log_report_completion(
        session_id: str, 
        total_tokens: int, 
        total_duration_sec: float, 
        status: str = "success",
        error: Optional[str] = None
    ):
        """Log metrics for the completion of an entire report."""
        msg = (
            f"[METRIC] report_completed | session={session_id} | status={status} | "
            f"total_tokens={total_tokens} | total_duration={total_duration_sec:.2f}s"
        )
        if error:
            sanitized_error = error.replace("|", "\\|").replace("\n", "\\n")
            msg += f" | error={sanitized_error}"
        
        logger.info(msg)

    @staticmethod
    def log_token_usage_warning(session_id: str, current_tokens: int, limit: int):
        """Log a warning when approaching or hitting the global token budget."""
        logger.warning(
            f"[METRIC] token_budget_warning | session={session_id} | "
            f"current={current_tokens} | limit={limit}"
        )
