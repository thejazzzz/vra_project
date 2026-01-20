# services/schema/relation_ontology.py
from enum import Enum, auto
from typing import Dict, Optional, NamedTuple

class CausalStrength(Enum):
    """
    Defines the strength of the causal claim.
    This prevents the system from confusing 'correlation' with 'causation'.
    """
    ASSOCIATIVE = "associative"       # A is related to B (weakest)
    CORRELATIONAL = "correlational"   # A and B appear together frequently
    CAUSAL = "causal"                 # A causes/influences B (strongest)

class RelationProperties(NamedTuple):
    label: str
    polarity: int  # 1 (Positive), -1 (Negative), 0 (Neutral)
    strength: CausalStrength
    symmetric: bool
    inverse: Optional[str] = None

# Comprehensive Map of Relations -> Research Properties
RELATION_PROPERTIES: Dict[str, RelationProperties] = {
    # --- Positive Causal (Strong) ---
    "improves": RelationProperties("improves", 1, CausalStrength.CAUSAL, False, "degraded_by"),
    "enables": RelationProperties("enables", 1, CausalStrength.CAUSAL, False, "enabled_by"),
    "causes": RelationProperties("causes", 1, CausalStrength.CAUSAL, False, "caused_by"),
    "supports": RelationProperties("supports", 1, CausalStrength.CAUSAL, False, "refutes"),
    "outperforms": RelationProperties("outperforms", 1, CausalStrength.CAUSAL, False, "outperformed_by"),
    
    # --- Negative Causal (Strong) ---
    "degrades": RelationProperties("degrades", -1, CausalStrength.CAUSAL, False, "improved_by"),
    "inhibits": RelationProperties("inhibits", -1, CausalStrength.CAUSAL, False, "promotes"),
    "refutes": RelationProperties("refutes", -1, CausalStrength.CAUSAL, False, "supports"),
    "contradicts": RelationProperties("contradicts", -1, CausalStrength.CAUSAL, True, "contradicts"), # Symmetric conflict
    
    # --- Structural/Hierarchical (Associative) ---
    "extends": RelationProperties("extends", 1, CausalStrength.ASSOCIATIVE, False, "extended_by"),
    "uses": RelationProperties("uses", 0, CausalStrength.ASSOCIATIVE, False, "used_by"),
    "includes": RelationProperties("includes", 0, CausalStrength.ASSOCIATIVE, False, "part_of"),
    "part_of": RelationProperties("part_of", 0, CausalStrength.ASSOCIATIVE, False, "includes"),
    "instance_of": RelationProperties("instance_of", 0, CausalStrength.ASSOCIATIVE, False, "has_instance"),
    
    # --- Correlational (Weak) ---
    "related_to": RelationProperties("related_to", 0, CausalStrength.CORRELATIONAL, True, "related_to"),
    "associated_with": RelationProperties("associated_with", 0, CausalStrength.CORRELATIONAL, True, "associated_with"),
    "co-occurs_with": RelationProperties("co-occurs_with", 0, CausalStrength.CORRELATIONAL, True, "co-occurs_with"),
}

def normalize_relation(relation: str) -> str:
    """Normalize raw LLM relation string to a known ontology key."""
    rel = relation.strip().lower().replace(" ", "_")
    # Quick Aliases
    aliases = {
        "builds_on": "extends",
        "based_on": "extends",
        "utilizes": "uses",
        "employs": "uses",
        "hampers": "inhibits",
        "prevents": "inhibits",
        "increases": "improves", # Context dependent, but usually 'improves metric'
        "decreases": "degrades", # Context dependent
    }
    return aliases.get(rel, rel)

def get_relation_props(relation: str) -> RelationProperties:
    """Get properties for a relation, defaulting to weak association if unknown."""
    norm = normalize_relation(relation)
    return RELATION_PROPERTIES.get(norm, RelationProperties(
        label=norm,
        polarity=0,
        strength=CausalStrength.ASSOCIATIVE,
        symmetric=False
    ))
