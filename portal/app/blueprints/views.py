from flask import Blueprint
from flask import request
from flask import flash
from flask import url_for
from flask import redirect
from flask import render_template

from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from app.util import strip_or_none
from app.util import str_empty
from app.util import permission_required

from app.model import Ticket
from app.model import Mode
from app.model import Permission
from app.model import Message
from app.model import ProblemType

from datetime import datetime

from app.extensions import db
from werkzeug.datastructures import ImmutableMultiDict

import sys

views = Blueprint('views', __name__)

@views.route("/")
def index():
    messages = Message.query.filter(Message.start_date < datetime.now(), Message.end_date > datetime.now())
    return render_template('index.html', messages=messages)

@views.route('/create-ticket', methods=['POST', 'GET'])
def create_ticket():
    """
    Serves the HTTP route /create-ticket. Shows a ticket create form on GET request.
    Submits a ticket on POST request with a form containing the following fields:
    - email: Email address of user
    - fullname: Full name of user
    - course: Course relevant to the ticket submission
    - section: Section of course relevant to the ticket submission
    - assignment: Name of assignment relevant to the ticket submission
    - question: Detailed questions relevant to the ticket submission
    - problem: Type of problem needed help with
    - mode: Whether the student is online or in-person

    Then redirects back to the home page.

    Utilizes the flask funciton 'render_template' to render
    the passed in create-ticket.html template which is the form that students use to create/submit tickets.

    Student login is required to access this page.
    """
    if request.method == 'GET':
        # Render create-ticket template if GET request or if there was an error in submission data
        return render_template('create-ticket.html')

    ticket = _attempt_create_ticket(request.form)

    if ticket:
        try:
            db.session.add(ticket)
            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            flash('Could not submit ticket, invalid data', category='error')

        except Exception as e:
            flash('Could not submit ticket, unknown reason', category='error')
            print(f'Failed to create ticket: {e}', file=sys.stderr)

        else:
            flash('Ticket created successfully!', category='success')
            return redirect(url_for('views.index'))

    return redirect(url_for('views.create_ticket'))

@views.route('/view-tickets')
@permission_required(Permission.Tutor)
def view_tickets():
    """
    Serves the HTTP route /view-tickets. This function queries the Tickets database and passes the result query
    to the front end to display all of the availabe tickets in the database.

    Utilizes the flask funciton 'render_template' to render the passed in view-tickets.html template which is
    used to display all tickets to tutors to be able to claim individual tickets.

    Student login is required to access this page.
    """
    tickets = Ticket.query.all()
    return render_template('view_tickets.html', tickets=tickets)

@views.route('/update-ticket', methods=["POST"])
@permission_required(Permission.Tutor)
def update_ticket():
    """
    This function handles the HTTP request when a tutor hits the claim, close, or reopen buttons on tickets
    :return: Render template to the original view-ticket.html page.
    """
    # get the tutors to display for edit ticket modal if the user presses it
    ticketID = request.form.get("ticketID")
    ticket: Ticket = Ticket.query.get(ticketID)

    # TODO: Check to make state is valid before changing it!!

    if ticket is None:
        flash('Could not update ticket status. Ticket not found in database.', category='error')

    elif request.form.get("action") == "Claim":
        ticket.claim(current_user)
        db.session.commit()
        flash('Ticket claimed!', category='info')

    elif request.form.get("action") == "Close":
        ticket.close()
        db.session.commit()
        flash('Ticket closed!', category='info')

    elif request.form.get("action") == "Open":
        ticket.reopen()
        db.session.commit()
        flash('Ticket opened!', category='info')

    else:
        flash('Did not change ticket status. Unknown action.', category='error')

    return redirect(url_for('views.view_tickets'))

@views.route('/edit-ticket', methods=["POST"])
@permission_required(Permission.Tutor)
def edit_ticket():
    # get ticket id back + current ticket
    ticketID = request.form.get("ticketIDModal")
    ticket = Ticket.query.get(ticketID)

    if ticket is not None:
        _attempt_edit_ticket(ticket)

    else:
        flash('Could not edit ticket. Ticket not found in database.', category='error')

    return redirect(url_for('views.view_tickets'))

# TODO: Use flask-wtf for form handling and validation
def _attempt_create_ticket(form: ImmutableMultiDict):
    """
    Given an HTML form as an ImmutableMultiDict, extracts, strips, and verifies the following values :
        - email: must be non-empty
        - fullname: must be non-empty
        - assignment: must be non-empty
        - question: must be non-empty
        - mode: must be valid model.Mode

        returns a Ticket object if values are valid, None otherwise.
    """

    # If the user is logged in, use their name and email
    if current_user.is_authenticated:
        email = current_user.email
        name = current_user.name

    # Otherwise get it from the form
    else:
        email = strip_or_none(form.get("email"))
        name = strip_or_none(form.get("fullname"))

    course = strip_or_none(form.get("course"))
    section = strip_or_none(form.get("section"))
    assignment = strip_or_none(form.get("assignment"))
    question = strip_or_none(form.get("question"))
    problem_id = strip_or_none(form.get("problem"))
    problem: ProblemType = ProblemType.query.get(problem_id)

    if str_empty(email):
        flash('Could not submit ticket, email must not be empty!', category='error')

    elif str_empty(name):
        flash('Could not submit ticket, name must not be empty!', category='error')

    elif str_empty(assignment):
        flash('Could not submit ticket, assignment name must not be empty!', category='error')

    elif str_empty(question):
        flash('Could not submit ticket, question must not be empty!', category='error')

    elif problem_id is not None and not problem:
        flash('Could not submit ticket, problem type is not valid!', category='error')

    # TODO: Check if course is a valid from a list of options
    # TODO: Check if section is valid from a list of options

    else:
        mode_val = strip_or_none(form.get("mode"))
        mode = None

        try:
            if mode_val:
                mode = Mode(int(mode_val))

        except ValueError:
            flash('Could not submit ticket, must select a valid mode!', category='error')

        else:
            return Ticket(email, name, course, section, assignment, question, problem_id, mode)

def _attempt_edit_ticket(ticket: Ticket):
    # get info back from popup modal form
    course = strip_or_none(request.form.get("courseField"))
    section = strip_or_none(request.form.get("sectionField"))
    assignment = strip_or_none(request.form.get("assignmentNameField"))
    question = strip_or_none(request.form.get("specificQuestionField"))
    primaryTutor = strip_or_none(request.form.get("primaryTutorInput"))
    tutorNotes = strip_or_none(request.form.get("tutorNotes"))
    wasSuccessful = strip_or_none(request.form.get("successfulSession"))
    problem_id = strip_or_none(request.form.get("problemTypeField"))
    problem: ProblemType = ProblemType.query.get(problem_id)

    # check for change in values from edit
    if course:
        # new info for course came back, update it for current ticket
        ticket.course = course

    if section:
        # new info for section came back, update it for current ticket
        ticket.section = section

    if assignment != ticket.assignment_name:
        # new info for assignment came back, update it for current ticket
        ticket.assignment_name = assignment

    if question != ticket.specific_question:
        # new info for question came back, update it for current ticket
        ticket.specific_question = question

    if problem:
        # new info for problem came back, update it for current ticket
        ticket.problem_type = problem_id

    if primaryTutor:
        # new info for primary tutor came back, update it for current ticket
        ticket.tutor_id = primaryTutor

    if tutorNotes:
        # new info for tutor notes came back, update it for current ticket
        ticket.tutor_notes = tutorNotes

    # new info for tutor notes came back, update it for current ticket
    ticket.successful_session = wasSuccessful is not None
    db.session.commit()
