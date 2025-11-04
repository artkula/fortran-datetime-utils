"""
Reviewer Web Application

Flask-based web interface for reviewing marked submissions and providing feedback.
"""

import base64
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from rich.console import Console

from aems.models.exam import StudentGrade, MarkResult, Verdict
from aems.memory import (
    Memory,
    MemoryStore,
    MemoryLevel,
    FeedbackType,
    generate_memory_id,
)


console = Console()


class ReviewerApp:
    """
    Web application for reviewing exam submissions.

    Provides interface for:
    - Viewing marked PDFs with annotations
    - Reviewing grading decisions
    - Overriding grades with rationale
    - Submitting "Improve checking" feedback
    - Managing memory layers
    """

    def __init__(
        self,
        marked_dir: Path,
        memory_dir: Path,
        course_id: str = "default",
        exam_id: str = "default",
        host: str = "127.0.0.1",
        port: int = 5000,
    ):
        """
        Initialize reviewer app.

        Args:
            marked_dir: Directory containing marked PDFs and results
            memory_dir: Directory for storing memories
            course_id: Course identifier
            exam_id: Exam identifier
            host: Host to bind to
            port: Port to listen on
        """
        self.marked_dir = Path(marked_dir)
        self.memory_dir = Path(memory_dir)
        self.course_id = course_id
        self.exam_id = exam_id
        self.host = host
        self.port = port

        # Initialize memory store
        self.memory_store = MemoryStore(memory_dir)

        # Create Flask app
        self.app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
        self.app.config['TEMPLATES_AUTO_RELOAD'] = True

        # Load submissions
        self.submissions = self._load_submissions()

        # Register routes
        self._register_routes()

    def _load_submissions(self) -> List[Dict[str, Any]]:
        """Load all grading results from marked directory."""
        submissions = []

        result_files = list(self.marked_dir.glob("*_results.yaml"))

        for result_file in result_files:
            try:
                with open(result_file, 'r') as f:
                    data = yaml.safe_load(f)
                    grade = StudentGrade(**data)

                    # Find corresponding PDF
                    student_id = grade.student_id
                    pdf_file = self.marked_dir / f"{student_id}_graded.pdf"

                    if not pdf_file.exists():
                        # Try without _graded suffix
                        pdf_file = self.marked_dir / f"{student_id}.pdf"

                    submission = {
                        'student_id': student_id,
                        'student_name': grade.student_name or student_id,
                        'grade': grade,
                        'pdf_path': pdf_file if pdf_file.exists() else None,
                        'result_file': result_file,
                        'needs_review': grade.needs_review,
                    }
                    submissions.append(submission)

            except Exception as e:
                console.print(f"[red]Error loading {result_file}: {e}[/red]")

        # Sort by needs_review first, then by student_id
        submissions.sort(key=lambda s: (not s['needs_review'], s['student_id']))

        return submissions

    def _register_routes(self):
        """Register Flask routes."""

        @self.app.route('/')
        def index():
            """Main page with list of submissions."""
            stats = {
                'total': len(self.submissions),
                'needs_review': sum(1 for s in self.submissions if s['needs_review']),
                'reviewed': sum(1 for s in self.submissions if not s['needs_review']),
            }

            return render_template('index.html', submissions=self.submissions, stats=stats)

        @self.app.route('/submission/<student_id>')
        def view_submission(student_id: str):
            """View a specific submission."""
            submission = None
            for s in self.submissions:
                if s['student_id'] == student_id:
                    submission = s
                    break

            if not submission:
                return "Submission not found", 404

            # Find prev/next for navigation
            current_idx = self.submissions.index(submission)
            prev_sub = self.submissions[current_idx - 1] if current_idx > 0 else None
            next_sub = self.submissions[current_idx + 1] if current_idx < len(self.submissions) - 1 else None

            return render_template(
                'submission.html',
                submission=submission,
                prev_sub=prev_sub,
                next_sub=next_sub,
                course_id=self.course_id,
                exam_id=self.exam_id,
            )

        @self.app.route('/pdf/<student_id>')
        def serve_pdf(student_id: str):
            """Serve marked PDF."""
            for submission in self.submissions:
                if submission['student_id'] == student_id:
                    pdf_path = submission.get('pdf_path')
                    if pdf_path and pdf_path.exists():
                        return send_file(pdf_path, mimetype='application/pdf')

            return "PDF not found", 404

        @self.app.route('/api/override', methods=['POST'])
        def override_grade():
            """Override a grade with feedback."""
            data = request.json

            student_id = data.get('student_id')
            check_id = data.get('check_id')
            new_verdict = data.get('verdict')
            new_points = data.get('points')
            rationale = data.get('rationale')
            reviewer_name = data.get('reviewer_name', 'anonymous')

            # Find the mark result
            submission = None
            for s in self.submissions:
                if s['student_id'] == student_id:
                    submission = s
                    break

            if not submission:
                return jsonify({'success': False, 'error': 'Submission not found'}), 404

            # Find the specific check
            mark_result = None
            for mr in submission['grade'].mark_results:
                if mr.check.id == check_id:
                    mark_result = mr
                    break

            if not mark_result:
                return jsonify({'success': False, 'error': 'Check not found'}), 404

            # Create memory for this override
            memory_id = generate_memory_id(
                level=MemoryLevel.QUESTION,
                course_id=self.course_id,
                exam_id=self.exam_id,
                question_id=mark_result.check.question_id,
                check_id=check_id,
            )

            memory = Memory(
                id=memory_id,
                level=MemoryLevel.QUESTION,
                course_id=self.course_id,
                exam_id=self.exam_id,
                question_id=mark_result.check.question_id,
                check_id=check_id,
                feedback_type=FeedbackType.GRADE_OVERRIDE,
                title=f"Override for {check_id}",
                description=rationale,
                original_verdict=mark_result.verdict,
                override_verdict=new_verdict,
                original_points=mark_result.points_awarded,
                override_points=float(new_points),
                rationale=rationale,
                created_by=reviewer_name,
            )

            # Store memory
            self.memory_store.store_memory(memory)

            # Update the grade (in memory, not persisted to file)
            mark_result.verdict = Verdict(new_verdict)
            mark_result.points_awarded = float(new_points)

            # Recalculate totals
            submission['grade'].total_points = sum(
                mr.points_awarded for mr in submission['grade'].mark_results
            )

            return jsonify({'success': True, 'memory_id': memory_id})

        @self.app.route('/api/feedback', methods=['POST'])
        def submit_feedback():
            """Submit 'Improve checking' feedback."""
            data = request.json

            check_id = data.get('check_id')
            question_id = data.get('question_id')
            feedback_text = data.get('feedback')
            feedback_type = data.get('type', 'improve_checking')
            reviewer_name = data.get('reviewer_name', 'anonymous')

            # Create memory
            memory_id = generate_memory_id(
                level=MemoryLevel.QUESTION,
                course_id=self.course_id,
                exam_id=self.exam_id,
                question_id=question_id,
                check_id=check_id,
            )

            memory = Memory(
                id=memory_id,
                level=MemoryLevel.QUESTION,
                course_id=self.course_id,
                exam_id=self.exam_id,
                question_id=question_id,
                check_id=check_id,
                feedback_type=FeedbackType(feedback_type),
                title=f"Feedback for {check_id}",
                description=feedback_text,
                created_by=reviewer_name,
            )

            self.memory_store.store_memory(memory)

            return jsonify({'success': True, 'memory_id': memory_id})

        @self.app.route('/api/memories')
        def list_memories():
            """List memories for a specific question/check."""
            question_id = request.args.get('question_id')
            check_id = request.args.get('check_id')

            from aems.memory import MemoryQuery

            query = MemoryQuery(
                level=MemoryLevel.QUESTION,
                course_id=self.course_id,
                exam_id=self.exam_id,
                question_id=question_id,
                check_id=check_id,
                limit=20,
            )

            memories = self.memory_store.query_memories(query)

            return jsonify({
                'memories': [m.model_dump(mode='json') for m in memories]
            })

    def run(self, debug: bool = False):
        """
        Start the web server.

        Args:
            debug: Enable debug mode
        """
        console.print(f"\n[bold blue]AEMS Reviewer[/bold blue]")
        console.print(f"Reviewing: {self.marked_dir}")
        console.print(f"Memory: {self.memory_dir}")
        console.print(f"\n[bold green]Starting server at http://{self.host}:{self.port}[/bold green]")
        console.print(f"Open your browser to view submissions.\n")

        self.app.run(host=self.host, port=self.port, debug=debug)
