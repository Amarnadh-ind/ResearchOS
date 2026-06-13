"""
Agent 5: Claim Extractor
Extracts verifiable claims with evidence from documents.
RULE-1: NO EVIDENCE = NO CLAIM
"""

from agents.base import BaseAgent
from services.llm import get_llm_client
from config.models import AgentRole
from schemas.agents import ExtractedClaim, ClaimExtractionOutput


CLAIM_SYSTEM = """You are a precise claim extraction system. Extract specific, verifiable claims from research documents.

CRITICAL RULE: Every claim MUST have supporting evidence from the source text. NO EVIDENCE = NO CLAIM.

Output valid JSON:
{
    "claims": [
        {
            "claim": "Specific factual claim",
            "evidence": "Direct quote or paraphrase from the source that supports this claim",
            "confidence": 0.0-1.0,
            "claim_type": "empirical|theoretical|methodological"
        }
    ]
}

Rules:
- Claims must be specific and verifiable
- Evidence must come directly from the source text
- Confidence reflects how strongly the evidence supports the claim
- Do NOT invent claims without textual evidence
- Prefer empirical claims over opinions
- Each claim should be a single, atomic statement"""


class ClaimExtractorAgent(BaseAgent):
    name = "claim_extractor"

    async def execute(self, input_data: dict, context: dict) -> dict:
        llm = get_llm_client()
        documents = input_data.get("documents", [])
        all_claims: list[ExtractedClaim] = []

        for doc in documents:
            summary = doc.get("summary", "")
            findings = doc.get("key_findings", [])
            sections = doc.get("sections", [])

            # Build content for extraction
            content_parts = [summary]
            content_parts.extend(findings)
            for section in sections:
                content_parts.append(section.get("content", ""))

            content = "\n".join(content_parts)[:6000]

            user_prompt = f"""Source: {doc.get('title', 'Unknown')}
URL: {doc.get('source_url', '')}

Content:
{content}

Extract all verifiable claims with supporting evidence."""

            try:
                result = await llm.complete_json(
                    role=AgentRole.CLAIM_EXTRACTOR,
                    system_prompt=CLAIM_SYSTEM,
                    user_prompt=user_prompt,
                )

                for claim_data in result.get("claims", []):
                    # RULE-1: Reject claims without evidence
                    if not claim_data.get("evidence"):
                        continue

                    claim = ExtractedClaim(
                        claim=claim_data["claim"],
                        evidence=claim_data["evidence"],
                        source_url=doc.get("source_url", ""),
                        source_title=doc.get("title", "Unknown"),
                        confidence=claim_data.get("confidence", 0.5),
                        claim_type=claim_data.get("claim_type", "empirical"),
                    )
                    all_claims.append(claim)
            except Exception:
                continue

        output = ClaimExtractionOutput(
            claims=all_claims,
            total_claims=len(all_claims),
        )
        return output.model_dump()

    def verify_output(self, output: dict) -> bool:
        if not super().verify_output(output):
            return False
        data = output.get("data", {})
        claims = data.get("claims", [])
        # Verify ALL claims have evidence (RULE-1)
        return all(c.get("evidence") for c in claims)
