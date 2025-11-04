"""
AEMS - Automated Exam Marking System

A privacy-conscious, multi-language, PDF-native automated exam marking system
for math/engineering courses with AI-powered grading.
"""

__version__ = "0.1.0"
__author__ = "AEMS Team"

from aems.models.exam import ExamPackage, MicroCheck, MarkResult, CanvasRow
from aems.models.annotations import AnnotationColor, AnnotationType, PDFAnnotation

__all__ = [
    "__version__",
    "__author__",
    "ExamPackage",
    "MicroCheck",
    "MarkResult",
    "CanvasRow",
    "AnnotationColor",
    "AnnotationType",
    "PDFAnnotation",
]
