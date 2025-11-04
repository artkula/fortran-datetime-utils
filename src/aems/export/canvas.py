"""
Canvas CSV Export

Converts AEMS grading results to Canvas-compatible gradebook CSV format.

Canvas CSV format:
- Student, ID, SIS User ID, SIS Login ID, Section, [Assignment columns...]
- Each assignment column contains the score
- Supports multiple questions as separate columns (Q1, Q2, etc.)
- Includes a Total column
"""

import csv
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
from rich.console import Console
from rich.table import Table

from aems.models.exam import StudentGrade, CanvasRow, QuestionScore


console = Console()


class CanvasExporter:
    """
    Exports grading results to Canvas-compatible CSV format.

    Handles aggregation of multiple questions and proper CSV formatting
    for Canvas LMS gradebook import.
    """

    def __init__(
        self,
        section: Optional[str] = None,
        assignment_name: Optional[str] = None,
    ):
        """
        Initialize Canvas exporter.

        Args:
            section: Optional section identifier for all students
            assignment_name: Optional assignment name prefix for columns
        """
        self.section = section
        self.assignment_name = assignment_name or "Exam"

    def load_grades_from_yaml(self, results_dir: Path) -> List[StudentGrade]:
        """
        Load grading results from YAML files in a directory.

        Args:
            results_dir: Directory containing *_results.yaml files

        Returns:
            List of StudentGrade objects
        """
        grades = []

        # Find all result YAML files
        result_files = list(results_dir.glob("*_results.yaml"))

        if not result_files:
            console.print(f"[yellow]Warning: No *_results.yaml files found in {results_dir}[/yellow]")
            return grades

        for result_file in result_files:
            try:
                with open(result_file, 'r') as f:
                    data = yaml.safe_load(f)
                    grade = StudentGrade(**data)
                    grades.append(grade)
            except Exception as e:
                console.print(f"[red]Error loading {result_file}: {e}[/red]")

        return grades

    def convert_to_canvas_rows(self, grades: List[StudentGrade]) -> List[CanvasRow]:
        """
        Convert StudentGrade objects to CanvasRow objects.

        Args:
            grades: List of StudentGrade objects

        Returns:
            List of CanvasRow objects with dynamic question columns
        """
        canvas_rows = []

        for grade in grades:
            # Build base row with required Canvas fields
            row_data = {
                "student": grade.student_name or grade.student_id,
                "id": grade.student_id,
                "sis_user_id": grade.sis_user_id or grade.student_id,
                "section": self.section or "",
            }

            # Add question scores as dynamic columns
            for q_score in grade.question_scores:
                # Use clean question ID as column name (e.g., Q1, Q2)
                col_name = self._format_question_column(q_score.question_id)
                row_data[col_name] = q_score.points_awarded

            # Add total score column
            row_data[f"{self.assignment_name} Total"] = grade.total_points

            # Mark for review if needed
            if grade.needs_review:
                row_data["Needs Review"] = "Yes"

            canvas_row = CanvasRow(**row_data)
            canvas_rows.append(canvas_row)

        return canvas_rows

    def _format_question_column(self, question_id: str) -> str:
        """
        Format question ID as a clean column name.

        Args:
            question_id: Question identifier (e.g., 'q1', 'question_1')

        Returns:
            Formatted column name (e.g., 'Q1')
        """
        # Strip common prefixes and format
        qid = question_id.lower().replace("question", "q").replace("_", "").replace("-", "")

        # Extract number if present
        import re
        match = re.search(r'(\d+)', qid)
        if match:
            num = match.group(1)
            return f"{self.assignment_name} Q{num}"

        # Fallback: use original ID
        return f"{self.assignment_name} {question_id}"

    def export_to_csv(
        self,
        grades: List[StudentGrade],
        output_path: Path,
        include_review_column: bool = True,
    ) -> None:
        """
        Export grades to Canvas CSV format.

        Args:
            grades: List of StudentGrade objects
            output_path: Path to output CSV file
            include_review_column: Whether to include 'Needs Review' column
        """
        if not grades:
            console.print("[yellow]No grades to export[/yellow]")
            return

        # Convert to Canvas rows
        canvas_rows = self.convert_to_canvas_rows(grades)

        # Determine all column names (dynamic based on questions)
        all_columns = self._get_all_columns(canvas_rows, include_review_column)

        # Write CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_columns)

            # Write header
            writer.writeheader()

            # Write rows
            for row in canvas_rows:
                row_dict = row.model_dump()

                # Ensure all columns are present (fill missing with empty string)
                for col in all_columns:
                    if col not in row_dict:
                        row_dict[col] = ""

                writer.writerow(row_dict)

        console.print(f"[green]✓[/green] Exported {len(canvas_rows)} grades to {output_path}")

    def _get_all_columns(self, rows: List[CanvasRow], include_review: bool) -> List[str]:
        """
        Get all column names from Canvas rows (including dynamic columns).

        Args:
            rows: List of CanvasRow objects
            include_review: Whether to include review column

        Returns:
            List of column names in proper order
        """
        # Start with required Canvas columns
        columns = ["Student", "ID", "SIS User ID", "SIS Login ID", "Section"]

        # Collect all dynamic question columns
        question_cols = set()
        total_col = None
        review_col = None

        for row in rows:
            row_dict = row.model_dump()
            for key in row_dict.keys():
                if key in ["student", "id", "sis_user_id", "section"]:
                    continue
                elif "Total" in key:
                    total_col = key
                elif "Needs Review" in key:
                    review_col = key
                else:
                    question_cols.add(key)

        # Sort question columns (Q1, Q2, Q3...)
        sorted_questions = sorted(question_cols, key=self._extract_question_number)
        columns.extend(sorted_questions)

        # Add total column
        if total_col:
            columns.append(total_col)

        # Add review column if requested
        if include_review and review_col:
            columns.append(review_col)

        return columns

    def _extract_question_number(self, col_name: str) -> int:
        """Extract question number from column name for sorting."""
        import re
        match = re.search(r'Q(\d+)', col_name)
        if match:
            return int(match.group(1))
        return 999  # Put unmatched at end

    def export_with_summary(
        self,
        grades: List[StudentGrade],
        output_path: Path,
    ) -> None:
        """
        Export grades and display summary statistics.

        Args:
            grades: List of StudentGrade objects
            output_path: Path to output CSV file
        """
        if not grades:
            console.print("[yellow]No grades to export[/yellow]")
            return

        # Export CSV
        self.export_to_csv(grades, output_path)

        # Display summary
        self._display_summary(grades)

    def _display_summary(self, grades: List[StudentGrade]) -> None:
        """Display summary statistics table."""
        console.print("\n[bold]Export Summary[/bold]")

        table = Table(show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        total_students = len(grades)
        needs_review_count = sum(1 for g in grades if g.needs_review)

        if grades:
            avg_score = sum(g.total_points for g in grades) / total_students
            avg_possible = sum(g.total_possible for g in grades) / total_students
            avg_percent = (avg_score / avg_possible * 100) if avg_possible > 0 else 0
        else:
            avg_score = avg_possible = avg_percent = 0

        table.add_row("Total Students", str(total_students))
        table.add_row("Average Score", f"{avg_score:.2f} / {avg_possible:.2f}")
        table.add_row("Average Percentage", f"{avg_percent:.1f}%")
        table.add_row("Needs Review", f"{needs_review_count} ({needs_review_count/total_students*100:.1f}%)")

        console.print(table)
        console.print()


def export_grades_to_canvas(
    results_dir: Path,
    output_path: Path,
    section: Optional[str] = None,
    assignment_name: Optional[str] = "Exam",
) -> None:
    """
    Convenience function to export grades from a results directory.

    Args:
        results_dir: Directory containing grading result YAML files
        output_path: Path to output CSV file
        section: Optional section identifier
        assignment_name: Optional assignment name prefix
    """
    exporter = CanvasExporter(section=section, assignment_name=assignment_name)
    grades = exporter.load_grades_from_yaml(results_dir)
    exporter.export_with_summary(grades, output_path)
