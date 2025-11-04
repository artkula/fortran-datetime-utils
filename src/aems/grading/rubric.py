"""
Rubric parsing and compilation into micro-checks.

Converts human-readable rubrics into structured, stepwise marking plans
with micro-checks, partial credit rules, and failure modes.
"""

import logging
import json
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

from aems.models.exam import MicroCheck

logger = logging.getLogger(__name__)


@dataclass
class RubricItem:
    """
    A single item in a rubric before compilation.

    This is the input format that instructors provide.
    """
    description: str
    points: float
    required: bool = True
    hints: List[str] = field(default_factory=list)
    common_errors: List[str] = field(default_factory=list)
    partial_credit_rules: Dict[str, float] = field(default_factory=dict)


@dataclass
class Rubric:
    """
    Complete rubric for a question or exam.

    Contains metadata and rubric items that will be compiled into micro-checks.
    """
    question_id: str
    title: str
    total_points: float
    items: List[RubricItem]
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "question_id": self.question_id,
            "title": self.title,
            "total_points": self.total_points,
            "items": [
                {
                    "description": item.description,
                    "points": item.points,
                    "required": item.required,
                    "hints": item.hints,
                    "common_errors": item.common_errors,
                    "partial_credit_rules": item.partial_credit_rules,
                }
                for item in self.items
            ],
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }


class RubricParser:
    """
    Parses rubrics from various formats (JSON, YAML, dict).

    Validates structure and converts to Rubric objects.
    """

    @staticmethod
    def parse_json(json_path: Path) -> Rubric:
        """
        Parse rubric from JSON file.

        Args:
            json_path: Path to JSON rubric file

        Returns:
            Rubric object
        """
        if not json_path.exists():
            raise FileNotFoundError(f"Rubric not found: {json_path}")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return RubricParser.parse_dict(data)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in rubric: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse rubric JSON: {e}")
            raise

    @staticmethod
    def parse_yaml(yaml_path: Path) -> Rubric:
        """
        Parse rubric from YAML file.

        Args:
            yaml_path: Path to YAML rubric file

        Returns:
            Rubric object
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"Rubric not found: {yaml_path}")

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return RubricParser.parse_dict(data)

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in rubric: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse rubric YAML: {e}")
            raise

    @staticmethod
    def parse_dict(data: Dict[str, Any]) -> Rubric:
        """
        Parse rubric from dictionary.

        Args:
            data: Dictionary with rubric data

        Returns:
            Rubric object
        """
        # Validate required fields
        required_fields = ["question_id", "title", "total_points", "items"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in rubric: {field}")

        # Parse rubric items
        items = []
        for item_data in data["items"]:
            item = RubricItem(
                description=item_data["description"],
                points=float(item_data["points"]),
                required=item_data.get("required", True),
                hints=item_data.get("hints", []),
                common_errors=item_data.get("common_errors", []),
                partial_credit_rules=item_data.get("partial_credit_rules", {}),
            )
            items.append(item)

        rubric = Rubric(
            question_id=data["question_id"],
            title=data["title"],
            total_points=float(data["total_points"]),
            items=items,
            dependencies=data.get("dependencies", {}),
            metadata=data.get("metadata", {}),
        )

        # Validate
        RubricParser.validate_rubric(rubric)

        return rubric

    @staticmethod
    def validate_rubric(rubric: Rubric) -> None:
        """
        Validate rubric consistency.

        Args:
            rubric: Rubric to validate

        Raises:
            ValueError: If rubric is invalid
        """
        # Check points add up (allow small floating point differences)
        total_from_items = sum(item.points for item in rubric.items)
        if abs(total_from_items - rubric.total_points) > 0.01:
            logger.warning(
                f"Rubric points mismatch: items sum to {total_from_items}, "
                f"but total_points is {rubric.total_points}"
            )

        # Check dependencies reference valid items
        item_ids = {f"{rubric.question_id}-{i:02d}" for i in range(len(rubric.items))}
        for check_id, deps in rubric.dependencies.items():
            for dep in deps:
                if dep not in item_ids:
                    logger.warning(f"Dependency {dep} not found in rubric items")


class RubricCompiler:
    """
    Compiles rubrics into structured micro-checks for grading.

    Converts instructor-friendly rubrics into machine-executable
    grading instructions.
    """

    def compile_rubric(
        self,
        rubric: Rubric,
        gold_solution_text: Optional[str] = None
    ) -> List[MicroCheck]:
        """
        Compile a rubric into micro-checks.

        Args:
            rubric: Rubric to compile
            gold_solution_text: Optional gold solution text for evidence extraction

        Returns:
            List of MicroCheck objects
        """
        micro_checks = []

        for idx, item in enumerate(rubric.items):
            check_id = f"{rubric.question_id}-{idx:02d}"

            # Extract evidence from gold solution if available
            evidence = ""
            if gold_solution_text:
                evidence = self._extract_evidence(
                    gold_solution_text,
                    item.description,
                    item.hints
                )

            # Build micro-check
            micro_check = MicroCheck(
                id=check_id,
                desc=item.description,
                points=item.points,
                evidence=evidence or item.description,
                failure_modes=item.common_errors,
                deps=rubric.dependencies.get(check_id, []),
                optional=not item.required,
            )

            micro_checks.append(micro_check)

        logger.info(
            f"Compiled {len(micro_checks)} micro-checks for {rubric.question_id}"
        )

        return micro_checks

    def _extract_evidence(
        self,
        gold_solution: str,
        description: str,
        hints: List[str]
    ) -> str:
        """
        Extract relevant evidence from gold solution.

        This is a simple keyword-based extraction. In future versions,
        this could use LLM to intelligently extract relevant portions.

        Args:
            gold_solution: Complete gold solution text
            description: Check description
            hints: Hint keywords

        Returns:
            Extracted evidence string
        """
        # Simple implementation: look for keywords in gold solution
        keywords = []

        # Extract keywords from description
        words = description.lower().split()
        keywords.extend([w for w in words if len(w) > 4])

        # Add hints
        keywords.extend([h.lower() for h in hints])

        if not keywords:
            return description

        # Find sentences containing keywords
        sentences = gold_solution.split(".")
        relevant_sentences = []

        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in keywords):
                relevant_sentences.append(sentence.strip())

        if relevant_sentences:
            return ". ".join(relevant_sentences[:2])  # First 2 relevant sentences

        return description

    def compile_to_yaml(
        self,
        micro_checks: List[MicroCheck],
        output_path: Path
    ) -> None:
        """
        Save compiled micro-checks to YAML file.

        Args:
            micro_checks: List of MicroCheck objects
            output_path: Output file path
        """
        data = {
            "micro_checks": [
                {
                    "id": check.id,
                    "description": check.desc,
                    "points": check.points,
                    "evidence": check.evidence,
                    "failure_modes": check.failure_modes,
                    "dependencies": check.deps,
                    "optional": check.optional,
                }
                for check in micro_checks
            ]
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved compiled checks to {output_path}")

    def compile_to_json(
        self,
        micro_checks: List[MicroCheck],
        output_path: Path
    ) -> None:
        """
        Save compiled micro-checks to JSON file.

        Args:
            micro_checks: List of MicroCheck objects
            output_path: Output file path
        """
        data = {
            "micro_checks": [
                {
                    "id": check.id,
                    "description": check.desc,
                    "points": check.points,
                    "evidence": check.evidence,
                    "failure_modes": check.failure_modes,
                    "dependencies": check.deps,
                    "optional": check.optional,
                }
                for check in micro_checks
            ]
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved compiled checks to {output_path}")


# Convenience functions
def parse_rubric(rubric_path: Path) -> Rubric:
    """
    Parse a rubric file (auto-detect format from extension).

    Args:
        rubric_path: Path to rubric file (.json, .yaml, .yml)

    Returns:
        Rubric object
    """
    suffix = rubric_path.suffix.lower()

    if suffix == ".json":
        return RubricParser.parse_json(rubric_path)
    elif suffix in [".yaml", ".yml"]:
        return RubricParser.parse_yaml(rubric_path)
    else:
        raise ValueError(f"Unsupported rubric format: {suffix}")


def compile_rubric(
    rubric: Rubric,
    gold_solution_text: Optional[str] = None
) -> List[MicroCheck]:
    """
    Compile a rubric into micro-checks.

    Args:
        rubric: Rubric to compile
        gold_solution_text: Optional gold solution text

    Returns:
        List of MicroCheck objects
    """
    compiler = RubricCompiler()
    return compiler.compile_rubric(rubric, gold_solution_text)


def compile_rubric_file(
    rubric_path: Path,
    gold_solution_text: Optional[str] = None,
    output_path: Optional[Path] = None,
    output_format: str = "yaml"
) -> List[MicroCheck]:
    """
    Parse and compile a rubric file.

    Args:
        rubric_path: Path to rubric file
        gold_solution_text: Optional gold solution text
        output_path: Optional output path for compiled checks
        output_format: Output format ('yaml' or 'json')

    Returns:
        List of MicroCheck objects
    """
    rubric = parse_rubric(rubric_path)
    compiler = RubricCompiler()
    micro_checks = compiler.compile_rubric(rubric, gold_solution_text)

    if output_path:
        if output_format == "yaml":
            compiler.compile_to_yaml(micro_checks, output_path)
        elif output_format == "json":
            compiler.compile_to_json(micro_checks, output_path)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    return micro_checks
