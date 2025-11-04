"""
Memory Store

Persistent storage and retrieval of learnings and feedback.
Uses YAML files for simplicity and human readability.
"""

import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

from rich.console import Console

from .models import (
    Memory,
    MemoryLevel,
    MemoryQuery,
    FeedbackType,
    EquivalenceRule,
    GradingPolicy,
    CommonError,
)


console = Console()


class MemoryStore:
    """
    Storage and retrieval system for memories across different levels.

    Stores memories in a hierarchical file structure:
    - memory_dir/
      - course_{id}/
        - course.yaml (course-level policies)
        - exam_{id}/
          - exam.yaml (exam-level rules)
          - question_{id}/
            - question.yaml (question-specific learnings)
            - checks.yaml (check-specific feedback)
      - user_{id}/
        - preferences.yaml (user preferences)
    """

    def __init__(self, memory_dir: Path):
        """
        Initialize memory store.

        Args:
            memory_dir: Root directory for storing memories
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def store_memory(self, memory: Memory) -> None:
        """
        Store a memory in the appropriate location based on level.

        Args:
            memory: Memory object to store
        """
        file_path = self._get_memory_file_path(memory)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing memories
        memories = []
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                memories = [Memory(**m) for m in data.get('memories', [])]

        # Check if memory with same ID exists
        existing_idx = None
        for idx, m in enumerate(memories):
            if m.id == memory.id:
                existing_idx = idx
                break

        if existing_idx is not None:
            # Update existing memory
            memories[existing_idx] = memory
        else:
            # Add new memory
            memories.append(memory)

        # Save back to file
        data = {
            'level': memory.level,
            'updated_at': datetime.now().isoformat(),
            'memories': [m.model_dump(mode='json') for m in memories]
        }

        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓[/green] Memory stored: {memory.title}")

    def query_memories(self, query: MemoryQuery) -> List[Memory]:
        """
        Query memories based on criteria.

        Args:
            query: Query parameters

        Returns:
            List of matching memories, sorted by relevance
        """
        memories = []

        # Determine which files to search based on query
        search_paths = self._get_search_paths(query)

        for path in search_paths:
            if path.exists():
                with open(path, 'r') as f:
                    data = yaml.safe_load(f) or {}
                    for m_data in data.get('memories', []):
                        memory = Memory(**m_data)
                        if self._matches_query(memory, query):
                            memories.append(memory)

        # Sort by relevance (applied_count desc, then confidence desc)
        memories.sort(
            key=lambda m: (m.applied_count, m.confidence),
            reverse=True
        )

        # Apply limit
        if query.limit:
            memories = memories[:query.limit]

        return memories

    def get_relevant_context(
        self,
        course_id: Optional[str] = None,
        exam_id: Optional[str] = None,
        question_id: Optional[str] = None,
        check_id: Optional[str] = None,
    ) -> str:
        """
        Get relevant memory context for grading.

        Retrieves memories from all applicable levels and formats
        them as a context string for the LLM.

        Args:
            course_id: Course identifier
            exam_id: Exam identifier
            question_id: Question identifier
            check_id: Check identifier

        Returns:
            Formatted context string
        """
        context_parts = []

        # Query each level
        queries = []

        if course_id:
            queries.append(MemoryQuery(
                level=MemoryLevel.COURSE,
                course_id=course_id,
                limit=5
            ))

        if exam_id:
            queries.append(MemoryQuery(
                level=MemoryLevel.EXAM,
                course_id=course_id,
                exam_id=exam_id,
                limit=10
            ))

        if question_id:
            queries.append(MemoryQuery(
                level=MemoryLevel.QUESTION,
                course_id=course_id,
                exam_id=exam_id,
                question_id=question_id,
                limit=15
            ))

        # Collect memories
        all_memories = []
        for query in queries:
            memories = self.query_memories(query)
            all_memories.extend(memories)

        if not all_memories:
            return ""

        # Format as context
        context_parts.append("**Previous Learnings:**\n")

        for memory in all_memories:
            context_parts.append(f"- [{memory.feedback_type}] {memory.title}")
            if memory.description:
                context_parts.append(f"  {memory.description}")
            if memory.original_verdict and memory.override_verdict:
                context_parts.append(
                    f"  Originally: {memory.original_verdict} "
                    f"→ Corrected: {memory.override_verdict}"
                )
            context_parts.append("")

        return "\n".join(context_parts)

    def increment_applied_count(self, memory_id: str) -> None:
        """
        Increment the applied count for a memory.

        Called when a memory is successfully applied to a grading decision.

        Args:
            memory_id: ID of the memory to update
        """
        # Search all memory files for this ID
        for yaml_file in self.memory_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f) or {}
                    memories = data.get('memories', [])

                updated = False
                for m_data in memories:
                    if m_data.get('id') == memory_id:
                        m_data['applied_count'] = m_data.get('applied_count', 0) + 1
                        updated = True
                        break

                if updated:
                    data['memories'] = memories
                    with open(yaml_file, 'w') as f:
                        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
                    return

            except Exception as e:
                console.print(f"[yellow]Warning: Error updating {yaml_file}: {e}[/yellow]")

    def _get_memory_file_path(self, memory: Memory) -> Path:
        """Determine file path for a memory based on its level."""
        if memory.level == MemoryLevel.COURSE:
            course_dir = self.memory_dir / f"course_{memory.course_id}"
            return course_dir / "course.yaml"

        elif memory.level == MemoryLevel.EXAM:
            exam_dir = (
                self.memory_dir
                / f"course_{memory.course_id}"
                / f"exam_{memory.exam_id}"
            )
            return exam_dir / "exam.yaml"

        elif memory.level == MemoryLevel.QUESTION:
            question_dir = (
                self.memory_dir
                / f"course_{memory.course_id}"
                / f"exam_{memory.exam_id}"
                / f"question_{memory.question_id}"
            )
            if memory.check_id:
                return question_dir / "checks.yaml"
            else:
                return question_dir / "question.yaml"

        elif memory.level == MemoryLevel.USER:
            user_dir = self.memory_dir / f"user_{memory.user_id}"
            return user_dir / "preferences.yaml"

        else:
            raise ValueError(f"Unknown memory level: {memory.level}")

    def _get_search_paths(self, query: MemoryQuery) -> List[Path]:
        """Get list of paths to search based on query."""
        paths = []

        if query.level == MemoryLevel.COURSE and query.course_id:
            paths.append(
                self.memory_dir / f"course_{query.course_id}" / "course.yaml"
            )

        elif query.level == MemoryLevel.EXAM and query.course_id and query.exam_id:
            paths.append(
                self.memory_dir
                / f"course_{query.course_id}"
                / f"exam_{query.exam_id}"
                / "exam.yaml"
            )

        elif query.level == MemoryLevel.QUESTION and query.question_id:
            base_dir = (
                self.memory_dir
                / f"course_{query.course_id}"
                / f"exam_{query.exam_id}"
                / f"question_{query.question_id}"
            )
            paths.extend([
                base_dir / "question.yaml",
                base_dir / "checks.yaml"
            ])

        elif query.level == MemoryLevel.USER and query.user_id:
            paths.append(
                self.memory_dir / f"user_{query.user_id}" / "preferences.yaml"
            )

        else:
            # Search all relevant levels
            if query.course_id:
                course_dir = self.memory_dir / f"course_{query.course_id}"
                if course_dir.exists():
                    paths.extend(course_dir.rglob("*.yaml"))

        return [p for p in paths if p.exists()]

    def _matches_query(self, memory: Memory, query: MemoryQuery) -> bool:
        """Check if memory matches query criteria."""
        # Check confidence
        if memory.confidence < query.min_confidence:
            return False

        # Check feedback type
        if query.feedback_type and memory.feedback_type != query.feedback_type:
            return False

        # Check IDs
        if query.course_id and memory.course_id != query.course_id:
            return False
        if query.exam_id and memory.exam_id != query.exam_id:
            return False
        if query.question_id and memory.question_id != query.question_id:
            return False
        if query.check_id and memory.check_id != query.check_id:
            return False
        if query.user_id and memory.user_id != query.user_id:
            return False

        # Check tags
        if query.tags:
            if not any(tag in memory.tags for tag in query.tags):
                return False

        return True


def generate_memory_id(
    level: MemoryLevel,
    course_id: Optional[str] = None,
    exam_id: Optional[str] = None,
    question_id: Optional[str] = None,
    check_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> str:
    """
    Generate a unique memory ID.

    Args:
        level: Memory level
        course_id: Course identifier
        exam_id: Exam identifier
        question_id: Question identifier
        check_id: Check identifier
        timestamp: Optional timestamp (defaults to now)

    Returns:
        Unique memory ID
    """
    if timestamp is None:
        timestamp = datetime.now()

    components = [
        level,
        course_id or "",
        exam_id or "",
        question_id or "",
        check_id or "",
        timestamp.isoformat(),
    ]

    # Create hash of components
    content = "|".join(str(c) for c in components)
    hash_hex = hashlib.sha256(content.encode()).hexdigest()[:12]

    return f"mem-{level}-{hash_hex}"
