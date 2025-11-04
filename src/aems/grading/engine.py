"""
Grading engine with stepwise RAG-based evaluation.

Uses LLM providers to evaluate student work against compiled micro-checks
with confidence scoring and amber flagging for uncertainty.
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from aems.models.exam import MicroCheck, MarkResult, Verdict, ProviderMetadata
from aems.providers import LLMProvider, LLMMessage, get_provider
from aems.models.annotations import BBox
from aems.memory import MemoryStore

logger = logging.getLogger(__name__)


class GradingEngine:
    """
    Stepwise grading engine with RAG over micro-checks.

    Evaluates student work step-by-step using LLM with grounding
    in the compiled rubric and gold solution.
    """

    # System prompt for grading
    GRADING_SYSTEM_PROMPT = """You are an expert exam grader for technical courses (math, engineering, physics).

Your task is to evaluate student work against specific grading criteria (micro-checks) with precision and fairness.

**Grading Principles:**
1. Be PRECISE: Focus only on the specific check being evaluated
2. Be FAIR: Award partial credit when work shows understanding despite errors
3. Be CERTAIN: Mark as UNCERTAIN if you cannot confidently judge
4. Be EXPLICIT: Reference specific parts of student work in your rationale

**Output Format:**
For each check, provide:
- Verdict: PASS, FAIL, or UNCERTAIN
- Points: Awarded points (can be partial)
- Rationale: Brief explanation with specific references
- Where: Location in student work (if applicable)

**When to mark UNCERTAIN:**
- Student work is illegible or unclear
- Novel solution method that needs expert review
- Ambiguous notation or terminology
- Low OCR confidence on critical parts"""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        temperature: float = 0.2,
        memory_store: Optional[MemoryStore] = None,
        course_id: Optional[str] = None,
        exam_id: Optional[str] = None,
    ):
        """
        Initialize grading engine.

        Args:
            provider: LLM provider (if None, uses default from config)
            temperature: Temperature for grading (low for determinism)
            memory_store: Optional memory store for retrieving past learnings
            course_id: Course identifier for memory context
            exam_id: Exam identifier for memory context
        """
        self.provider = provider or get_provider()
        self.temperature = temperature
        self.memory_store = memory_store
        self.course_id = course_id
        self.exam_id = exam_id
        logger.info(f"Initialized grading engine with {self.provider.model}")
        if memory_store:
            logger.info(f"Memory integration enabled for course={course_id}, exam={exam_id}")

    def grade_check(
        self,
        student_work: str,
        micro_check: MicroCheck,
        student_id: str,
        question_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> MarkResult:
        """
        Grade student work against a single micro-check.

        Args:
            student_work: Student's work text (from OCR)
            micro_check: MicroCheck to evaluate against
            student_id: Student identifier
            question_id: Question identifier
            context: Additional context (OCR confidence, metadata, etc.)

        Returns:
            MarkResult with verdict and rationale
        """
        # Build grading prompt
        prompt = self._build_check_prompt(student_work, micro_check, context)

        # Call LLM
        try:
            messages = [LLMMessage(role="user", content=prompt)]
            response = self.provider.chat(
                messages=messages,
                system=self.GRADING_SYSTEM_PROMPT,
                temperature=self.temperature,
            )

            # Parse response
            verdict, points, rationale = self._parse_grading_response(
                response.text,
                micro_check
            )

            # Create provider metadata
            provider_meta = ProviderMetadata(
                provider=self.provider.__class__.__name__,
                model=response.model,
                temperature=self.temperature,
                tokens_used=response.tokens_used,
            )

            # Create mark result
            result = MarkResult(
                student_id=student_id,
                question_id=question_id,
                check_id=micro_check.id,
                verdict=verdict,
                points_awarded=points,
                rationale=rationale,
                provider_meta=provider_meta,
                ocr_confidence=context.get("ocr_confidence") if context else None,
            )

            logger.debug(
                f"Graded {micro_check.id}: {verdict.value}, "
                f"{points}/{micro_check.points} pts"
            )

            return result

        except Exception as e:
            logger.error(f"Grading failed for {micro_check.id}: {e}")
            # Return uncertain result on error
            return MarkResult(
                student_id=student_id,
                question_id=question_id,
                check_id=micro_check.id,
                verdict=Verdict.UNCERTAIN,
                points_awarded=0.0,
                rationale=f"Grading error: {str(e)}",
            )

    def _build_check_prompt(
        self,
        student_work: str,
        micro_check: MicroCheck,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the prompt for grading a specific check.

        Args:
            student_work: Student's work text
            micro_check: MicroCheck to evaluate
            context: Additional context

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # Check details
        prompt_parts.append("**GRADING CHECK:**")
        prompt_parts.append(f"Check ID: {micro_check.id}")
        prompt_parts.append(f"Description: {micro_check.desc}")
        prompt_parts.append(f"Points: {micro_check.points}")

        # Expected evidence from gold solution
        if micro_check.evidence:
            prompt_parts.append(f"\n**EXPECTED (from gold solution):**")
            prompt_parts.append(micro_check.evidence)

        # Common failure modes
        if micro_check.failure_modes:
            prompt_parts.append(f"\n**COMMON ERRORS TO CHECK FOR:**")
            for error in micro_check.failure_modes:
                prompt_parts.append(f"- {error}")

        # Memory context from past learnings
        if self.memory_store and self.course_id and self.exam_id:
            memory_context = self.memory_store.get_relevant_context(
                course_id=self.course_id,
                exam_id=self.exam_id,
                question_id=micro_check.question_id,
                check_id=micro_check.id,
            )
            if memory_context:
                prompt_parts.append(f"\n{memory_context}")

        # Student work
        prompt_parts.append(f"\n**STUDENT WORK:**")
        prompt_parts.append(student_work)

        # Context (OCR confidence, etc.)
        if context:
            if "ocr_confidence" in context:
                conf = context["ocr_confidence"]
                if conf < 0.8:
                    prompt_parts.append(f"\n**NOTE:** OCR confidence is low ({conf:.1%}), mark UNCERTAIN if unclear")

        # Request
        prompt_parts.append("\n**YOUR EVALUATION:**")
        prompt_parts.append("Provide:")
        prompt_parts.append("1. Verdict: PASS, FAIL, or UNCERTAIN")
        prompt_parts.append("2. Points: Awarded points (0 to " + str(micro_check.points) + ")")
        prompt_parts.append("3. Rationale: Brief explanation with specific references")

        return "\n".join(prompt_parts)

    def _parse_grading_response(
        self,
        response_text: str,
        micro_check: MicroCheck,
    ) -> tuple[Verdict, float, str]:
        """
        Parse LLM response into structured grading result.

        Args:
            response_text: LLM response text
            micro_check: The micro-check being evaluated

        Returns:
            Tuple of (verdict, points, rationale)
        """
        response_lower = response_text.lower()

        # Parse verdict
        verdict = Verdict.UNCERTAIN
        if "verdict: pass" in response_lower or "verdict pass" in response_lower:
            verdict = Verdict.PASS
        elif "verdict: fail" in response_lower or "verdict fail" in response_lower:
            verdict = Verdict.FAIL
        elif "verdict: uncertain" in response_lower or "verdict uncertain" in response_lower:
            verdict = Verdict.UNCERTAIN

        # Parse points (look for patterns like "Points: 2.0" or "2.0 points")
        points = 0.0
        lines = response_text.split("\n")
        for line in lines:
            line_lower = line.lower()
            if "points:" in line_lower or "awarded:" in line_lower:
                # Extract number
                import re
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    try:
                        points = float(numbers[0])
                        points = min(points, micro_check.points)  # Cap at max
                        break
                    except ValueError:
                        pass

        # Default points based on verdict if not found
        if points == 0.0:
            if verdict == Verdict.PASS:
                points = micro_check.points
            elif verdict == Verdict.FAIL:
                points = 0.0
            # UNCERTAIN stays at 0.0

        # Extract rationale (everything after "Rationale:" or similar)
        rationale = response_text
        for keyword in ["rationale:", "explanation:", "reasoning:"]:
            if keyword in response_lower:
                idx = response_lower.index(keyword) + len(keyword)
                rationale = response_text[idx:].strip()
                # Take first paragraph
                rationale = rationale.split("\n\n")[0].strip()
                break

        # Fallback: use full response if no specific rationale found
        if rationale == response_text:
            rationale = response_text[:200]  # Truncate

        return verdict, points, rationale

    def grade_question(
        self,
        student_work: str,
        micro_checks: List[MicroCheck],
        student_id: str,
        question_id: str,
    ) -> List[MarkResult]:
        """
        Grade all checks for a question.

        Args:
            student_work: Student's complete work for the question
            micro_checks: List of micro-checks to evaluate
            student_id: Student identifier
            question_id: Question identifier

        Returns:
            List of MarkResult objects
        """
        results = []

        for check in micro_checks:
            result = self.grade_check(
                student_work=student_work,
                micro_check=check,
                student_id=student_id,
                question_id=question_id,
            )
            results.append(result)

        total_awarded = sum(r.points_awarded for r in results)
        total_possible = sum(c.points for c in micro_checks)

        logger.info(
            f"Graded {question_id} for {student_id}: "
            f"{total_awarded:.1f}/{total_possible:.1f} pts, "
            f"{sum(1 for r in results if r.verdict == Verdict.UNCERTAIN)} uncertain"
        )

        return results


# Convenience function
def grade_student_work(
    student_work: str,
    micro_checks: List[MicroCheck],
    student_id: str,
    question_id: str,
    provider: Optional[LLMProvider] = None,
) -> List[MarkResult]:
    """
    Grade student work against micro-checks.

    Args:
        student_work: Student's work text
        micro_checks: List of micro-checks
        student_id: Student identifier
        question_id: Question identifier
        provider: Optional LLM provider

    Returns:
        List of MarkResult objects
    """
    engine = GradingEngine(provider=provider)
    return engine.grade_question(
        student_work,
        micro_checks,
        student_id,
        question_id,
    )
