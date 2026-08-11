"""Engagement classification helpers."""

from __future__ import annotations

import re


NEGATIVE = ("bad", "terrible", "hate", "angry", "complaint", "refund", "scam", "worst", "broken", "issue")
POSITIVE = ("great", "love", "awesome", "thanks", "thank you", "amazing", "excellent", "helpful")
QUESTION = ("?", "how", "what", "when", "where", "which", "can you", "do you", "is there")
SALES = ("price", "pricing", "cost", "quote", "demo", "buy", "purchase", "plan", "trial", "subscribe")
SUPPORT = ("help", "support", "not working", "error", "bug", "unable", "can't", "cannot", "issue")
SPAM = ("crypto", "forex", "nft", "click here", "dm me for", "make money")
PARTNERSHIP = ("partner", "collab", "collaboration", "affiliate", "sponsorship")


def classify_text(body: str) -> dict[str, str | int]:
    text = (body or "").strip().lower()
    sentiment = "neutral"
    if any(w in text for w in NEGATIVE):
        sentiment = "negative"
    elif any(w in text for w in POSITIVE):
        sentiment = "positive"

    intent = "other"
    if any(w in text for w in SPAM):
        intent = "spam"
    elif any(w in text for w in SALES):
        intent = "sales_enquiry"
    elif any(w in text for w in SUPPORT):
        intent = "support"
    elif any(w in text for w in PARTNERSHIP):
        intent = "partnership"
    elif any(w in text for w in QUESTION) or "?" in text:
        intent = "question"
    elif sentiment == "negative":
        intent = "complaint"
    elif sentiment == "positive":
        intent = "praise"

    priority = "medium"
    lead_probability = 20
    if intent == "spam":
        priority = "low"
        lead_probability = 0
    elif intent == "complaint" or sentiment == "negative":
        priority = "high"
        lead_probability = 35
    elif intent == "sales_enquiry":
        priority = "high"
        lead_probability = 80
    elif intent == "support":
        priority = "high"
        lead_probability = 40
    elif intent == "partnership":
        priority = "medium"
        lead_probability = 55
    elif intent == "question":
        priority = "medium"
        lead_probability = 45
    elif intent == "praise":
        priority = "low"
        lead_probability = 15

    if re.search(r"\burgent\b|\basap\b|\bimmediately\b", text):
        priority = "critical"
        lead_probability = max(lead_probability, 60)

    return {
        "sentiment": sentiment,
        "intent": intent,
        "priority": priority,
        "lead_probability": lead_probability,
    }
