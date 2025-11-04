"""
Tests for core data models.
"""

import pytest
from aems.models.exam import (
    ExamPackage,
    MicroCheck,
    MarkResult,
    Verdict,
    CanvasRow,
    StudentGrade,
    QuestionScore,
)


def test_micro_check_creation():
    """Test MicroCheck model creation."""
    check = MicroCheck(
        id="Q1a-01",
        desc="Applies Newton's second law correctly",
        points=2.0,
        evidence="F = ma equation",
        failure_modes=["sign error", "unit error"],
        deps=["Q1a-00"],
    )

    assert check.id == "Q1a-01"
    assert check.points == 2.0
    assert len(check.failure_modes) == 2
    assert "sign error" in check.failure_modes


def test_micro_check_validation():
    """Test MicroCheck validation."""
    # Points must be non-negative
    with pytest.raises(Exception):  # Pydantic validation error
        MicroCheck(
            id="Q1-01",
            desc="Test",
            points=-1.0,
            evidence="Test",
        )


def test_mark_result_creation():
    """Test MarkResult model creation."""
    result = MarkResult(
        student_id="student_001",
        question_id="Q1a",
        check_id="Q1a-01",
        verdict=Verdict.PASS,
        points_awarded=2.0,
        rationale="Correct application of F=ma",
    )

    assert result.verdict == Verdict.PASS
    assert result.points_awarded == 2.0
    assert result.student_id == "student_001"


def test_canvas_row_creation():
    """Test CanvasRow model creation."""
    row = CanvasRow(
        student="Smith, John",
        id="12345",
        sis_user_id="SIS12345",
        section="MECH101-A",
    )

    assert row.student == "Smith, John"
    assert row.sis_user_id == "SIS12345"


def test_canvas_row_with_grades():
    """Test CanvasRow with dynamic grade columns."""
    row = CanvasRow(
        student="Smith, John",
        id="12345",
        sis_user_id="SIS12345",
        Q1=8.0,
        Q2=7.5,
        Q3=9.0,
        Total=24.5,
    )

    data = row.to_dict()
    assert data["Q1"] == 8.0
    assert data["Q2"] == 7.5
    assert data["Total"] == 24.5


def test_canvas_row_from_student_grade():
    """Test creating CanvasRow from StudentGrade."""
    # Create a student grade
    grade = StudentGrade(
        student_id="12345",
        student_name="John Smith",
        sis_user_id="SIS12345",
        question_scores=[
            QuestionScore(question_id="Q1", points_awarded=8, points_possible=10, num_checks=5, num_uncertain=0),
            QuestionScore(question_id="Q2", points_awarded=7, points_possible=10, num_checks=5, num_uncertain=1),
        ],
        total_points=15,
        total_possible=20,
    )

    # Convert to Canvas row
    row = CanvasRow.from_student_grade(grade, section="MECH101-A")

    assert row.student == "Smith, John"  # Last, First format
    assert row.id == "12345"
    assert row.sis_user_id == "SIS12345"
    assert row.section == "MECH101-A"

    data = row.to_dict()
    assert data["Q1"] == 8
    assert data["Q2"] == 7
    assert data["Total"] == 15
