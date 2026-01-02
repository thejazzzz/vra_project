#File: services/reporting/length_controller.py
from dataclasses import dataclass
from typing import Dict

@dataclass
class PageBudget:
    total_pages: int
    section_token_limits: Dict[str, int]
class ReportLengthController:
    """
    Manages token budgets to target a specific page count.
    Assumption: 1 Page approx 500 words approx 700 tokens (conservative).
    """
    
    TOKENS_PER_PAGE = 700
    
    # Weights for distribution (must sum to ~1.0 excluding appendix)
    SECTION_WEIGHTS = {
        "exec_summary": 0.05,
        "trend_analysis": 0.30,
        "gap_analysis": 0.25,
        "network_analysis": 0.20, 
        "limitations": 0.05,
        # Introduction / Deep Dives / etc. fill the rest
        "default": 0.15 
    }

    @staticmethod
    def calculate_budget(target_pages: int = 15) -> PageBudget:
        total_tokens = target_pages * ReportLengthController.TOKENS_PER_PAGE
        
        budgets = {}
        for section, weight in ReportLengthController.SECTION_WEIGHTS.items():
            budgets[section] = int(total_tokens * weight)
            
        return PageBudget(
            total_pages=target_pages,
            section_token_limits=budgets
        )
