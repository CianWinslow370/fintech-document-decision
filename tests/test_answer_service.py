from src.answer_service import decide_action


def test_high_risk_policy_requires_review():
    evidence = [{"text": "Manual approval required", "risk": "high"}]
    assert decide_action(evidence) == "review"
