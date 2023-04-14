from flask import Blueprint
from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
from .. import model as m
import datetime
from app.extensions import db

views = Blueprint('views', __name__)

def now():
    # gets the current time in UTC
    UTC = datetime.timezone.utc
    now = datetime.datetime.now(UTC)
    return now

@views.route('/create-ticket')
@login_required
def create_ticket():
    return render_template('create-ticket.html')

@views.route('/open-tickets', methods=["POST"])
@login_required
def open_tickets():
    email = request.form.get("emailAdressField")
    firstName = request.form.get("firstNameField")
    lastName = request.form.get("lastNameField")
    course = request.form.get("courseField")
    section = request.form.get("sectionField")
    assignment = request.form.get("assignmentNameField")
    question = request.form.get("specificQuestionField")
    problem = request.form.get("problemTypeField")
    mode = request.form['modeOfTicket']
    print(f"Following ticket information has been created:\n{lastName}\n{firstName}\n{email}\n{course}\n{section}\n{assignment}\n{question}\n{problem}\n{mode}")

    # create ticket with info sent back
    if request.method == "POST":
        ticket = m.Ticket(
            email,
            firstName,
            course,
            section,
            assignment,
            question,
            problem,
            now(),
            mode)

        # insert into 'Tickets' table
        db.session.add(ticket)
        db.session.commit()

    return render_template('open-tickets.html', email=email, firstName=firstName, lastName=lastName, course=course,
                           section=section, assignmentName=assignment, specificQuestion=question, problemType=problem, mode=mode)

@views.route('/view-tickets')
@login_required
def view_tickets():
    """
    This funciton handels the HTTP route /view-tickets, which is a page for tutors to view all tickets
    Tickets from all statuses will be returned including recently closed ones.
    Admin will be able to choose how long closed tickets should remain in the view-tickets view.
    """
    # get all tickets
    tickets = m.Ticket.query.all()
    return render_template('view_tickets.html', tickets=tickets, m=m, user=current_user)

@views.route('/update-ticket', methods=["GET", "POST"])
@login_required
def update_ticket():
    """
    This function handles the HTTP request when a tutor hits the claim, close, or reopen buttons on tickets
    :return: Render template to the original view-ticket.html page.
    """
    tickets = m.Ticket.query.all()
    tutor = current_user
    ticketID = request.form.get("ticketID")

    print("RECIEVED TICKET ID: " + str(ticketID))
    print("VALUE OF ACTION: " + str(request.form.get("action")))
    # retrieve ticket by primary key using get()
    current_ticket = m.Ticket.query.get(ticketID)

    if request.form.get("action") == "Claim":
        # edit status of ticket to Claimed, and assign tutor
        current_ticket.tutor_id = tutor.id
        current_ticket.status = m.Status.Claimed
        db.session.commit()

        print("TUTOR ID THAT CLAIMED TICKET: " + str(current_ticket.tutor_id))
    elif request.form.get("action") == "Close":
        # edit status of ticket to CLOSED,
        # TODO: calculate session duration and assign to ticket.session_duration
        current_ticket.status = m.Status.Closed
        db.session.commit()
    elif request.form.get("action") == "ReOpen":
        # edit status of ticket back to OPEN
        current_ticket.status = m.Status.Open
        db.session.commit()

    return render_template('view_tickets.html', tickets=tickets, m=m, user=current_user)
