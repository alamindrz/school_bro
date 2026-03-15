"""
Results App Interfaces - Contracts for other apps
NO model imports. Pure data contracts.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import date


@dataclass
class ResultContract:
    """
    Contract for a single result entry
    """
    student_id: int
    subject_id: int
    ca1_score: Optional[int] = None
    ca2_score: Optional[int] = None
    ca3_score: Optional[int] = None
    exam_score: Optional[int] = None
    practical_score: Optional[int] = None
    project_score: Optional[int] = None


@dataclass
class ResultSheetContract:
    """
    Contract for result sheet creation
    """
    class_id: int
    session_id: int
    term_id: int
    subject_ids: List[int]


@dataclass
class StudentPerformanceContract:
    """
    Contract for student performance summary
    """
    student_id: int
    session_id: Optional[int] = None
    term_id: Optional[int] = None
    average: float = 0
    total_score: int = 0
    position: int = 0
    grade: str = ""
    remark: str = ""


class ResultsServiceInterface:
    """
    Interface that other apps must use to interact with results app
    """
    
    @staticmethod
    def get_student_results(
        student_id: int,
        session_id: Optional[int] = None,
        term_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get results for a student"""
        raise NotImplementedError("Use results.selectors.ResultSelector.get_student_results")
    
    @staticmethod
    def get_student_performance(
        student_id: int,
        session_id: Optional[int] = None
    ) -> StudentPerformanceContract:
        """Get performance summary for a student"""
        raise NotImplementedError("Use results.selectors.CumulativeSelector.get_student_summary")
    
    @staticmethod
    def check_result_availability(
        student_id: int,
        session_id: int,
        term_id: int
    ) -> bool:
        """Check if results are available for a student"""
        raise NotImplementedError("Use results.selectors.ResultSelector.check_availability")