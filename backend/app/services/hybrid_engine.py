"""
Hybrid Reconciliation Engine - Phase 5.2

Pure logic, no DB access - takes a rule engine tier and an ML engine
tier, returns the reconciled final tier and whether human review is
required. See rule_score_service.py's counterpart for the DB-wiring
layer that calls this and builds a FinalVerdict row.

Locked reconciliation table:
    safe   + safe        -> safe,       no review
    any    + same tier    -> that tier, no review
    low    + high (either)-> high,      no review (more cautious wins)
    safe   + low  (either)-> low,       no review (more cautious wins)
    safe   + high (either)-> NO VERDICT, REVIEW REQUIRED
"""

from dataclasses import dataclass
from app.services.rule_engine import RiskTier


@dataclass
class HybridResult:
    final_tier: RiskTier | None  # None only when requires_review is True
    requires_review: bool


def reconcile(rule_tier: RiskTier, ml_tier: RiskTier) -> HybridResult:
    """Applies the locked reconciliation table to a pair of engine tiers."""
    tier_pair = {rule_tier, ml_tier}

    if rule_tier == ml_tier:
        return HybridResult(final_tier=rule_tier, requires_review=False)

    if tier_pair == {RiskTier.SAFE, RiskTier.HIGH_RISK}:
        # The one genuine disagreement worth a human's attention.
        return HybridResult(final_tier=None, requires_review=True)

    if tier_pair == {RiskTier.SAFE, RiskTier.LOW_RISK}:
        return HybridResult(final_tier=RiskTier.LOW_RISK, requires_review=False)

    if tier_pair == {RiskTier.LOW_RISK, RiskTier.HIGH_RISK}:
        return HybridResult(final_tier=RiskTier.HIGH_RISK, requires_review=False)

    # Defensive fallback - should be unreachable with only 3 valid tiers,
    # but never silently guess on an unrecognised combination.
    return HybridResult(final_tier=None, requires_review=True)