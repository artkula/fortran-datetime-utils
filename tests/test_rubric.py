"""
Tests for rubric parsing and compilation.
"""

import pytest
import json
import yaml
from pathlib import Path
from aems.grading.rubric import (
    Rubric,
    RubricItem,
    RubricParser,
    RubricCompiler,
    parse_rubric,
    compile_rubric,
    compile_rubric_file,
)
from aems.models.exam import MicroCheck


def test_rubric_item_creation():
    """Test RubricItem creation."""
    item = RubricItem(
        description="Check force diagram",
        points=2.0,
        required=True,
        hints=["forces", "diagram"],
        common_errors=["Missing friction"],
        partial_credit_rules={"Minor error": 1.5},
    )

    assert item.description == "Check force diagram"
    assert item.points == 2.0
    assert item.required is True
    assert len(item.hints) == 2
    assert len(item.common_errors) == 1


def test_rubric_creation():
    """Test Rubric creation."""
    item1 = RubricItem("Step 1", 2.0)
    item2 = RubricItem("Step 2", 3.0)

    rubric = Rubric(
        question_id="Q1",
        title="Test Question",
        total_points=5.0,
        items=[item1, item2],
    )

    assert rubric.question_id == "Q1"
    assert rubric.title == "Test Question"
    assert rubric.total_points == 5.0
    assert len(rubric.items) == 2


def test_rubric_to_dict():
    """Test Rubric to_dict conversion."""
    item = RubricItem("Check answer", 1.0)
    rubric = Rubric(
        question_id="Q1",
        title="Test",
        total_points=1.0,
        items=[item],
    )

    data = rubric.to_dict()

    assert data["question_id"] == "Q1"
    assert data["title"] == "Test"
    assert data["total_points"] == 1.0
    assert len(data["items"]) == 1


def test_parse_dict():
    """Test parsing rubric from dictionary."""
    data = {
        "question_id": "Q1",
        "title": "Test Question",
        "total_points": 5.0,
        "items": [
            {
                "description": "Step 1",
                "points": 2.0,
                "required": True,
                "hints": ["hint1"],
                "common_errors": ["error1"],
                "partial_credit_rules": {},
            },
            {
                "description": "Step 2",
                "points": 3.0,
            },
        ],
    }

    rubric = RubricParser.parse_dict(data)

    assert rubric.question_id == "Q1"
    assert len(rubric.items) == 2
    assert rubric.items[0].points == 2.0
    assert rubric.items[1].points == 3.0


def test_parse_dict_missing_field():
    """Test parsing fails with missing required field."""
    data = {
        "question_id": "Q1",
        "title": "Test",
        # Missing total_points and items
    }

    with pytest.raises(ValueError, match="Missing required field"):
        RubricParser.parse_dict(data)


def test_validate_rubric_points_mismatch():
    """Test rubric validation catches point mismatches."""
    item1 = RubricItem("Step 1", 2.0)
    item2 = RubricItem("Step 2", 3.0)

    # Items sum to 5, but total_points is 10
    rubric = Rubric(
        question_id="Q1",
        title="Test",
        total_points=10.0,  # Mismatch!
        items=[item1, item2],
    )

    # Should log warning but not raise
    RubricParser.validate_rubric(rubric)


def test_compile_rubric():
    """Test compiling rubric into micro-checks."""
    item1 = RubricItem(
        description="Draw free body diagram",
        points=2.0,
        common_errors=["Missing forces"],
    )
    item2 = RubricItem(
        description="Calculate forces",
        points=3.0,
        hints=["equilibrium"],
    )

    rubric = Rubric(
        question_id="Q2",
        title="Statics",
        total_points=5.0,
        items=[item1, item2],
    )

    compiler = RubricCompiler()
    checks = compiler.compile_rubric(rubric)

    assert len(checks) == 2
    assert checks[0].id == "Q2-00"
    assert checks[0].desc == "Draw free body diagram"
    assert checks[0].points == 2.0
    assert "Missing forces" in checks[0].failure_modes

    assert checks[1].id == "Q2-01"
    assert checks[1].points == 3.0


def test_compile_with_gold_solution():
    """Test compiling with gold solution text for evidence extraction."""
    item = RubricItem(
        description="Apply Newton's second law",
        points=3.0,
        hints=["F=ma", "force"],
    )

    rubric = Rubric(
        question_id="Q1",
        title="Newton's Law",
        total_points=3.0,
        items=[item],
    )

    gold_solution = """
    First, we apply Newton's second law: F = ma.
    The net force is 100N and mass is 10kg.
    Therefore, acceleration a = F/m = 100/10 = 10 m/s².
    """

    compiler = RubricCompiler()
    checks = compiler.compile_rubric(rubric, gold_solution)

    assert len(checks) == 1
    # Evidence should contain something from gold solution
    assert len(checks[0].evidence) > 0


def test_compile_with_dependencies():
    """Test that dependencies are preserved in micro-checks."""
    items = [
        RubricItem("Step 1", 1.0),
        RubricItem("Step 2", 1.0),
        RubricItem("Step 3", 1.0),
    ]

    rubric = Rubric(
        question_id="Q1",
        title="Test",
        total_points=3.0,
        items=items,
        dependencies={
            "Q1-01": ["Q1-00"],  # Step 2 depends on Step 1
            "Q1-02": ["Q1-01"],  # Step 3 depends on Step 2
        },
    )

    compiler = RubricCompiler()
    checks = compiler.compile_rubric(rubric)

    assert checks[1].deps == ["Q1-00"]
    assert checks[2].deps == ["Q1-01"]


def test_compile_optional_checks():
    """Test that optional items are marked correctly."""
    items = [
        RubricItem("Required step", 2.0, required=True),
        RubricItem("Optional verification", 1.0, required=False),
    ]

    rubric = Rubric(
        question_id="Q1",
        title="Test",
        total_points=3.0,
        items=items,
    )

    compiler = RubricCompiler()
    checks = compiler.compile_rubric(rubric)

    assert checks[0].optional is False
    assert checks[1].optional is True


def test_parse_json_file(tmp_path):
    """Test parsing rubric from JSON file."""
    json_data = {
        "question_id": "Q1",
        "title": "Test",
        "total_points": 2.0,
        "items": [
            {"description": "Step 1", "points": 1.0},
            {"description": "Step 2", "points": 1.0},
        ],
    }

    json_file = tmp_path / "rubric.json"
    with open(json_file, "w") as f:
        json.dump(json_data, f)

    rubric = RubricParser.parse_json(json_file)

    assert rubric.question_id == "Q1"
    assert len(rubric.items) == 2


def test_parse_yaml_file(tmp_path):
    """Test parsing rubric from YAML file."""
    yaml_data = {
        "question_id": "Q1",
        "title": "Test",
        "total_points": 2.0,
        "items": [
            {"description": "Step 1", "points": 1.0},
            {"description": "Step 2", "points": 1.0},
        ],
    }

    yaml_file = tmp_path / "rubric.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(yaml_data, f)

    rubric = RubricParser.parse_yaml(yaml_file)

    assert rubric.question_id == "Q1"
    assert len(rubric.items) == 2


def test_parse_rubric_convenience(tmp_path):
    """Test convenience parse_rubric function with auto-detection."""
    data = {
        "question_id": "Q1",
        "title": "Test",
        "total_points": 1.0,
        "items": [{"description": "Step", "points": 1.0}],
    }

    # Test JSON
    json_file = tmp_path / "test.json"
    with open(json_file, "w") as f:
        json.dump(data, f)

    rubric_json = parse_rubric(json_file)
    assert rubric_json.question_id == "Q1"

    # Test YAML
    yaml_file = tmp_path / "test.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(data, f)

    rubric_yaml = parse_rubric(yaml_file)
    assert rubric_yaml.question_id == "Q1"


def test_compile_to_yaml(tmp_path):
    """Test saving compiled checks to YAML."""
    checks = [
        MicroCheck(
            id="Q1-00",
            desc="Step 1",
            points=1.0,
            evidence="test",
            failure_modes=["error1"],
            deps=[],
        )
    ]

    output_file = tmp_path / "checks.yaml"
    compiler = RubricCompiler()
    compiler.compile_to_yaml(checks, output_file)

    assert output_file.exists()

    # Verify contents
    with open(output_file) as f:
        data = yaml.safe_load(f)

    assert "micro_checks" in data
    assert len(data["micro_checks"]) == 1
    assert data["micro_checks"][0]["id"] == "Q1-00"


def test_compile_to_json(tmp_path):
    """Test saving compiled checks to JSON."""
    checks = [
        MicroCheck(
            id="Q1-00",
            desc="Step 1",
            points=1.0,
            evidence="test",
            failure_modes=[],
            deps=[],
        )
    ]

    output_file = tmp_path / "checks.json"
    compiler = RubricCompiler()
    compiler.compile_to_json(checks, output_file)

    assert output_file.exists()

    # Verify contents
    with open(output_file) as f:
        data = json.load(f)

    assert "micro_checks" in data
    assert len(data["micro_checks"]) == 1


def test_compile_rubric_file_integration(tmp_path):
    """Test end-to-end rubric file compilation."""
    rubric_data = {
        "question_id": "Q1",
        "title": "Integration Test",
        "total_points": 3.0,
        "items": [
            {"description": "Part A", "points": 1.5},
            {"description": "Part B", "points": 1.5},
        ],
    }

    rubric_file = tmp_path / "rubric.json"
    with open(rubric_file, "w") as f:
        json.dump(rubric_data, f)

    output_file = tmp_path / "checks.yaml"

    checks = compile_rubric_file(
        rubric_file,
        output_path=output_file,
        output_format="yaml"
    )

    assert len(checks) == 2
    assert output_file.exists()


# Integration tests with example rubrics
def test_example_mechanics_rubric():
    """Test parsing the mechanics example rubric."""
    rubric_path = Path("examples/rubric_example_mechanics.yaml")
    if not rubric_path.exists():
        pytest.skip("Example rubric not found")

    rubric = parse_rubric(rubric_path)

    assert rubric.question_id == "Q2"
    assert rubric.total_points == 10.0
    assert len(rubric.items) == 6


def test_example_calculus_rubric():
    """Test parsing the calculus example rubric."""
    rubric_path = Path("examples/rubric_example_calculus.json")
    if not rubric_path.exists():
        pytest.skip("Example rubric not found")

    rubric = parse_rubric(rubric_path)

    assert rubric.question_id == "Q1"
    assert rubric.total_points == 8.0
    assert len(rubric.items) == 5
