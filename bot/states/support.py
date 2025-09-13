from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    """States for support interactions"""
    
    # Support ticket creation
    creating_ticket = State()
    selecting_ticket_category = State()
    entering_ticket_subject = State()
    entering_ticket_description = State()
    
    # FAQ interaction
    browsing_faq = State()
    searching_faq = State()
    
    # Feedback
    providing_feedback = State()
    entering_feedback_rating = State()
    entering_feedback_comment = State()
    
    # Technical support
    troubleshooting = State()
    entering_error_details = State()
    uploading_screenshot = State()
    
    # Contact admin
    contacting_admin = State()
    entering_admin_message = State()
    
    # Problem reporting
    reporting_problem = State()
    selecting_problem_type = State()
    describing_problem = State()
    
    # Service status check
    checking_service_status = State()
    
    # Connection troubleshooting
    troubleshooting_connection = State()
    entering_connection_details = State()