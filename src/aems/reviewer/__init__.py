"""
AEMS Reviewer - Web-based review interface

Provides a web UI for reviewing marked submissions, overriding grades,
and providing feedback to improve the grading system.
"""

from .app import ReviewerApp

__all__ = ["ReviewerApp"]
