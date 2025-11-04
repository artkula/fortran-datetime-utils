"""
Batch grading orchestrator for processing multiple student submissions.

Coordinates OCR, grading, and annotation for entire classes.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml

from aems.models.exam import MicroCheck, MarkResult, StudentGrade, QuestionScore, Verdict
from aems.models.annotations import AnnotationBatch, AnnotationType, AnnotationColor, BBox
from aems.grading.engine import GradingEngine
from aems.pdf import PDFReader, PDFAnnotator, extract_text
from aems.ocr import get_ocr_router
from aems.providers import get_provider

logger = logging.getLogger(__name__)


class BatchGrader:
    """
    Orchestrates batch grading of student submissions.

    Handles:
    - Loading compiled micro-checks
    - OCR of student PDFs
    - LLM-based grading
    - PDF annotation
    - Results aggregation
    """

    def __init__(
        self,
        checks_path: Path,
        provider_type: Optional[str] = None,
        temperature: float = 0.2,
    ):
        """
        Initialize batch grader.

        Args:
            checks_path: Path to compiled checks.yaml
            provider_type: LLM provider to use
            temperature: Grading temperature
        """
        self.checks_path = checks_path
        self.micro_checks = self._load_checks(checks_path)

        # Initialize grading engine
        provider = get_provider(provider_type) if provider_type else None
        self.grading_engine = GradingEngine(provider, temperature)

        # Initialize OCR router
        self.ocr_router = get_ocr_router()

        logger.info(
            f"Initialized batch grader with {len(self.micro_checks)} checks"
        )

    def _load_checks(self, checks_path: Path) -> List[MicroCheck]:
        """
        Load compiled micro-checks from YAML.

        Args:
            checks_path: Path to checks.yaml

        Returns:
            List of MicroCheck objects
        """
        if not checks_path.exists():
            raise FileNotFoundError(f"Checks file not found: {checks_path}")

        with open(checks_path, "r") as f:
            data = yaml.safe_load(f)

        checks = []
        for check_data in data.get("micro_checks", []):
            check = MicroCheck(
                id=check_data["id"],
                desc=check_data["description"],
                points=float(check_data["points"]),
                evidence=check_data.get("evidence", ""),
                failure_modes=check_data.get("failure_modes", []),
                deps=check_data.get("dependencies", []),
                optional=check_data.get("optional", False),
            )
            checks.append(check)

        return checks

    def grade_submission(
        self,
        pdf_path: Path,
        student_id: str,
        question_id: Optional[str] = None,
    ) -> StudentGrade:
        """
        Grade a single student submission.

        Args:
            pdf_path: Path to student PDF
            student_id: Student identifier
            question_id: Question ID (extracted from checks if None)

        Returns:
            StudentGrade with results
        """
        logger.info(f"Grading submission for {student_id}: {pdf_path.name}")

        # Extract text from PDF (simple version - full version would use layout detection)
        try:
            student_work = extract_text(pdf_path)
            logger.debug(f"Extracted {len(student_work)} characters from PDF")
        except Exception as e:
            logger.error(f"Failed to extract text: {e}")
            student_work = ""

        # Determine question ID
        if question_id is None:
            # Extract from first check ID (e.g., "Q1-00" -> "Q1")
            if self.micro_checks:
                question_id = self.micro_checks[0].id.split("-")[0]
            else:
                question_id = "Q1"

        # Grade all checks
        mark_results = self.grading_engine.grade_question(
            student_work=student_work,
            micro_checks=self.micro_checks,
            student_id=student_id,
            question_id=question_id,
        )

        # Aggregate results
        total_points = sum(r.points_awarded for r in mark_results)
        total_possible = sum(c.points for c in self.micro_checks)
        num_uncertain = sum(1 for r in mark_results if r.verdict == Verdict.UNCERTAIN)

        question_score = QuestionScore(
            question_id=question_id,
            points_awarded=total_points,
            points_possible=total_possible,
            num_checks=len(self.micro_checks),
            num_uncertain=num_uncertain,
        )

        grade = StudentGrade(
            student_id=student_id,
            student_name=None,  # TODO: Extract from PDF or metadata
            sis_user_id=student_id,
            question_scores=[question_score],
            total_points=total_points,
            total_possible=total_possible,
            mark_results=mark_results,
            needs_review=num_uncertain > 0,
        )

        logger.info(
            f"Graded {student_id}: {total_points:.1f}/{total_possible:.1f} pts, "
            f"{num_uncertain} uncertain"
        )

        return grade

    def annotate_pdf(
        self,
        pdf_path: Path,
        mark_results: List[MarkResult],
        output_path: Path,
    ) -> Path:
        """
        Annotate student PDF with grading results.

        Args:
            pdf_path: Input PDF path
            mark_results: Grading results
            output_path: Output PDF path

        Returns:
            Path to annotated PDF
        """
        batch = AnnotationBatch(pdf_path=str(pdf_path))

        # For now, add simple page-level annotations
        # TODO: Use bounding boxes from layout detection

        # Read PDF to get dimensions
        with PDFReader(pdf_path) as reader:
            if reader.page_count == 0:
                raise ValueError("PDF has no pages")

            width, height = reader.get_page_dimensions(0)

        # Create annotations based on verdicts
        y_pos = 50
        spacing = 60

        for result in mark_results:
            # Choose color based on verdict
            if result.verdict == Verdict.PASS:
                color = AnnotationColor.GREEN
                kind = AnnotationType.HIGHLIGHT
            elif result.verdict == Verdict.FAIL:
                color = AnnotationColor.RED
                kind = AnnotationType.SQUIGGLY
            else:  # UNCERTAIN
                color = AnnotationColor.AMBER
                kind = AnnotationType.TEXT

            # Create annotation
            bbox = BBox(x0=50, y0=y_pos, x1=width - 50, y1=y_pos + 40)

            comment = (
                f"{result.check_id}: {result.verdict.value} - "
                f"{result.points_awarded:.1f}/{self._get_check_points(result.check_id)} pts. "
                f"{result.rationale[:100]}"
            )

            batch.add_annotation(
                page_index=0,
                bbox=bbox,
                kind=kind,
                color=color,
                comment=comment,
                check_id=result.check_id,
            )

            y_pos += spacing

        # Apply annotations
        with PDFAnnotator(pdf_path) as annotator:
            annotator.add_annotations(batch.annotations)
            annotator.save(output_path)

        logger.info(f"Annotated PDF: {output_path}")
        return output_path

    def _get_check_points(self, check_id: str) -> float:
        """Get total points for a check ID."""
        for check in self.micro_checks:
            if check.id == check_id:
                return check.points
        return 0.0

    def grade_batch(
        self,
        input_dir: Path,
        output_dir: Path,
        pattern: str = "*.pdf",
    ) -> List[StudentGrade]:
        """
        Grade all PDFs in a directory.

        Args:
            input_dir: Directory with student PDFs
            output_dir: Directory for output
            pattern: File pattern to match

        Returns:
            List of StudentGrade objects
        """
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all PDFs
        pdf_files = list(input_dir.glob(pattern))
        logger.info(f"Found {len(pdf_files)} PDFs to grade")

        grades = []

        for pdf_path in pdf_files:
            # Extract student ID from filename
            student_id = pdf_path.stem

            try:
                # Grade submission
                grade = self.grade_submission(pdf_path, student_id)
                grades.append(grade)

                # Annotate PDF
                output_path = output_dir / f"{student_id}_graded.pdf"
                self.annotate_pdf(pdf_path, grade.mark_results, output_path)

            except Exception as e:
                logger.error(f"Failed to grade {pdf_path.name}: {e}")
                continue

        logger.info(f"Graded {len(grades)}/{len(pdf_files)} submissions")

        # Save results summary
        self._save_results_summary(grades, output_dir / "results.yaml")

        return grades

    def _save_results_summary(
        self,
        grades: List[StudentGrade],
        output_path: Path,
    ) -> None:
        """
        Save grading results summary to YAML.

        Args:
            grades: List of StudentGrade objects
            output_path: Output file path
        """
        summary = {
            "total_students": len(grades),
            "needs_review": sum(1 for g in grades if g.needs_review),
            "average_score": sum(g.total_points for g in grades) / len(grades) if grades else 0,
            "grades": [
                {
                    "student_id": g.student_id,
                    "total_points": g.total_points,
                    "total_possible": g.total_possible,
                    "percentage": (g.total_points / g.total_possible * 100) if g.total_possible > 0 else 0,
                    "needs_review": g.needs_review,
                }
                for g in grades
            ],
        }

        with open(output_path, "w") as f:
            yaml.dump(summary, f, default_flow_style=False)

        logger.info(f"Saved results summary: {output_path}")


# Convenience function
def grade_batch(
    checks_path: Path,
    input_dir: Path,
    output_dir: Path,
    provider_type: Optional[str] = None,
) -> List[StudentGrade]:
    """
    Grade a batch of student submissions.

    Args:
        checks_path: Path to compiled checks.yaml
        input_dir: Directory with student PDFs
        output_dir: Directory for output
        provider_type: LLM provider to use

    Returns:
        List of StudentGrade objects
    """
    grader = BatchGrader(checks_path, provider_type)
    return grader.grade_batch(input_dir, output_dir)
