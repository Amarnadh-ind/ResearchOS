"""
Agent 6: Critic Agent
Evaluates evidence quality and validates claims.
RULE-6: Critique phase mandatory.
"""

from agents.base import BaseAgent
from services.llm import get_llm_client
from config.models import AgentRole
from schemas.agents import CriticOutput, CritiqueResult


CRITIC_SYSTEM = """You are a rigorous academic critic. Evaluate each claim against its evidence.

For each claim, assess:
1. Is the evidence sufficient to support the claim?
2. What is the evidence quality (strong/moderate/weak/insufficient)?
3. Are there logical fallacies or unsupported leaps?
4. Should the claim be accepted or rejected?

STRICT JSON OUTPUT RULES:
- Return ONLY valid JSON. No markdown. No explanations before or after.
- No code fences (```). No commentary. ONLY the JSON object.
- All strings must be properly terminated with closing quotes.
- Escape special characters in strings: use \\" for quotes, \\n for newlines.
- Do NOT include trailing commas.
- Keep critique text concise to avoid unterminated strings.

Required JSON structure:
{
    "critiques": [
        {
            "claim": "The original claim text",
            "is_valid": true,
            "critique": "Detailed critique explaining the assessment",
            "evidence_quality": "strong",
            "suggested_verification": "How this could be further verified, or null"
        }
    ],
    "overall_evidence_quality": "strong",
    "rejected_claims": ["list of rejected claim texts"],
    "verified_claims": ["list of verified claim texts"]
}

Rules:
- Be rigorous but fair
- Reject claims with insufficient evidence
- Flag claims that require additional verification
- Evaluate logical consistency
- Check for circular reasoning or correlation/causation errors
- Keep each critique field under 200 words to ensure valid JSON"""


class CriticAgent(BaseAgent):
    name = "critic"

    async def execute(self, input_data: dict, context: dict) -> dict:
        llm = get_llm_client()
        claims = input_data.get("claims", [])

        if not claims:
            return CriticOutput(
                critiques=[],
                overall_evidence_quality="insufficient",
                rejected_claims=[],
                verified_claims=[],
            ).model_dump()

        # Format claims for critique
        claims_text = []
        for i, claim in enumerate(claims):
            claims_text.append(
                f"Claim {i+1}: {claim.get('claim', '')}\n"
                f"Evidence: {claim.get('evidence', '')}\n"
                f"Source: {claim.get('source_title', 'Unknown')}\n"
                f"Confidence: {claim.get('confidence', 0)}"
            )

        user_prompt = f"""Critically evaluate the following {len(claims)} claims:

{chr(10).join(claims_text)}

Provide a rigorous critique of each claim and its evidence.
Return ONLY valid JSON. No markdown. No explanations."""

        result = await llm.complete_json(
            role=AgentRole.CRITIC,
            system_prompt=CRITIC_SYSTEM,
            user_prompt=user_prompt,
        )

        critiques_list = []
        for c in result.get("critiques", []):
            if not isinstance(c, dict):
                continue
            
            # Extract claim
            claim_text = c.get("claim") or c.get("text") or ""
            
            # Extract is_valid with fallbacks
            is_valid = c.get("is_valid")
            if is_valid is None:
                is_valid = c.get("valid")
            if is_valid is None:
                is_valid = True
                
            # Extract critique text
            critique_text = c.get("critique") or c.get("assessment") or c.get("analysis") or "Evidence is sufficient to support the claim."
            
            # Extract evidence quality
            evidence_quality = c.get("evidence_quality") or c.get("quality") or "moderate"
            if evidence_quality not in ("strong", "moderate", "weak", "insufficient"):
                evidence_quality = "moderate"
                
            # Extract suggested verification
            suggested_verification = c.get("suggested_verification") or c.get("verification") or None
            
            critiques_list.append(CritiqueResult(
                claim=claim_text,
                is_valid=is_valid,
                critique=critique_text,
                evidence_quality=evidence_quality,
                suggested_verification=suggested_verification
            ))

        output = CriticOutput(
            critiques=critiques_list,
            overall_evidence_quality=result.get("overall_evidence_quality", "moderate"),
            rejected_claims=result.get("rejected_claims") or [],
            verified_claims=result.get("verified_claims") or [],
        )

        return output.model_dump()

    def verify_output(self, output: dict) -> bool:
        """RULE-6: Critique phase must produce results."""
        if not super().verify_output(output):
            return False
        data = output.get("data", {})
        return len(data.get("critiques", [])) > 0
