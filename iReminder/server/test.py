from syslog import closelog
import pytest
from flask import jsonify
from canvas import *

# run tests with coverage pytest --cov=. test.py

#token expiring on May 8th: 14559~KgbYlf8d9JUAPV5MJP6NiQpdShuIGyQNzkKtiR5QWlfVOxcWqIRdxttT8bgODWlT



example_assignment={'id': 495011, 
     'description': '', 
     'due_at': '2022-08-23T04:59:59Z', 
     'unlock_at': '2022-08-15T05:00:00Z', 
     'lock_at': '2023-01-16T05:59:00Z', 
     'points_possible': 1.0, 
     'grading_type': 'points', 
     'assignment_group_id': 57905, 
     'grading_standard_id': None, 
     'created_at': '2022-06-27T13:03:50Z', 
     'updated_at': '2023-01-05T14:17:34Z', 
     'peer_reviews': False, 
     'automatic_peer_reviews': False, 
     'position': 29, 
     'grade_group_students_individually': False, 
     'anonymous_peer_reviews': False, 
     'group_category_id': None, 
     'post_to_sis': False, 
     'moderated_grading': False, 
     'omit_from_final_grade': False, 
     'intra_group_peer_reviews': False, 
     'anonymous_instructor_annotations': False, 
     'anonymous_grading': False, 
     'graders_anonymous_to_graders': False, 
     'grader_count': 0, 
     'grader_comments_visible_to_graders': True, 
     'final_grader_id': None, 
     'grader_names_visible_to_final_grader': True, 
     'allowed_attempts': -1, 
     'annotatable_attachment_id': None, 
     'hide_in_gradebook': False, 
     'lock_info': {'lock_at': '2023-01-16T05:59:00Z', 'can_view': True, 'asset_string': 'assignment_495011'}, 
     'secure_params': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJsdGlfYXNzaWdubWVudF9pZCI6IjRlYjkzZDg1LTRkNWItNGExNC1hMDE0LWUwZGZhM2U0ZGE3MSJ9.fnjFKFvmbVLBzW3otYhQWL9PXCT4egn1jKurTFmK08E', 
     'lti_context_id': '4eb93d85-4d5b-4a14-a014-e0dfa3e4da71', 
     'course_id': 23873,
     'name': 'Week 1 Learning Objectives Quiz', 
     'submission_types': ['online_quiz'], 
     'has_submitted_submissions': True,
     'due_date_required': False, 
     'max_name_length': 255, 
     'in_closed_grading_period': False, 
     'graded_submissions_exist': True, 
     'is_quiz_assignment': True, 
     'can_duplicate': False, 
     'original_course_id': None, 
     'original_assignment_id': None, 
     'original_lti_resource_link_id': None, 
     'original_assignment_name': None, 
     'original_quiz_id': None, 
     'workflow_state': 'published', 
     'important_dates': False, 
     'muted': True, 
     'html_url': 'https://canvas.instructure.com/courses/23873/assignments/495011', 
     'quiz_id': 230268, 
     'anonymous_submissions': False, 
     'published': True, 
     'only_visible_to_overrides': False, 
     'visible_to_everyone': True, 
     'locked_for_user': True, 
     'lock_explanation': 'This assignment was locked Jan 15, 2023 at 11:59pm.', 
     'submissions_download_url': 'https://canvas.instructure.com/courses/23873/quizzes/230268/submissions?zip=1', 
     'post_manually': False, 
     'anonymize_students': False, 
     'require_lockdown_browser': False, 
     'restrict_quantitative_data': False}


def parse_assignment_date():
    course_name = "Fall 2022-CS 199-CA Training-Sections CAL, CAO"
    parsed_assignment = parse_assignment(example_assignment, course_name)
    assert parsed_assignment["DueDate"] == "08/23/2022"
