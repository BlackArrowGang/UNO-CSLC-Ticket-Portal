from flask import Flask
from flask.testing import FlaskClient

from app.model import Ticket
from app.model import Mode

import pytest

# TODO: Need to test more invalid input (e.g. long strings, etc.) break the database!

def test_create_ticket_post_with_no_auth(create_auth_client, app: Flask):

    auth_client = create_auth_client(name='John Doe', email='test@test.email')

    test_form_data = {
        'course':'course1',
        'section':'section1',
        'assignment':'assignment1',
        'question':'This is my question?',
        'problem':'1',
        'mode': Mode.InPerson.value
    }

    response = auth_client.post('/create-ticket', data=test_form_data)

    with app.app_context():
        assert Ticket.query.count() == 1

        ticket: Ticket = Ticket.query.first()
        assert ticket.student_email == 'test@test.email'
        assert ticket.student_name == 'John Doe'
        assert ticket.course == 'course1'
        assert ticket.section == 'section1'
        assert ticket.assignment_name == 'assignment1'
        assert ticket.specific_question == 'This is my question?'
        assert ticket.problem_type == 1
        assert ticket.mode == Mode.InPerson

    with auth_client.session_transaction() as session:
        flashes = session['_flashes']
        assert len(flashes) == 1

        (category, message) = flashes[0]
        assert category == 'success'
        assert message == 'Ticket created successfully!'

    # Expect redirect back to index
    assert '302' in response.status
    assert b'href="/"' in response.data

def test_create_ticket_no_data(auth_client: FlaskClient, app: Flask):
    response = auth_client.post('/create-ticket', data={})

    # We accept tickets as long as they have name and email for now
    with app.app_context():
        assert Ticket.query.count() == 1

    with auth_client.session_transaction() as session:
        flashes = session['_flashes']
        assert len(flashes) == 1

        (category, message) = flashes[0]
        assert category == 'success'
        assert message == 'Ticket created successfully!'

    # Expect redirect back to create ticket page
    assert '302' in response.status
    assert b'href="/"' in response.data

@pytest.fixture
def create_ticket_with_invalid_data(auth_client: FlaskClient, app: Flask):
    test_form_data = {
            'course':'course1',
            'section':'section1',
            'assignment':'assignment1',
            'question':'This is my question?',
            'problem':'1',
            'mode': Mode.InPerson.value
        }

    def _factory(**kwargs):
        for key, val in kwargs.items():
            test_form_data[key] = val

        response = auth_client.post('/create-ticket', data=test_form_data)

        with app.app_context():
            assert Ticket.query.count() == 0

        return response

    yield _factory

def test_create_ticket_empty_assignment(create_ticket_with_invalid_data, auth_client: FlaskClient):
    response = create_ticket_with_invalid_data(assignment='')

    with auth_client.session_transaction() as session:
        flashes = session['_flashes']
        assert len(flashes) == 1

        (category, message) = flashes[0]
        assert category == 'error'
        assert message == 'Could not submit ticket, assignment name must not be empty!'

    # Expect redirect back to create ticket page
    assert '302' in response.status
    assert b'href="/create-ticket"' in response.data

def test_create_ticket_empty_question(create_ticket_with_invalid_data, auth_client: FlaskClient):
    response = create_ticket_with_invalid_data(question='')

    with auth_client.session_transaction() as session:
        flashes = session['_flashes']
        assert len(flashes) == 1

        (category, message) = flashes[0]
        assert category == 'error'
        assert message == 'Could not submit ticket, question must not be empty!'

    # Expect redirect back to create ticket page
    assert '302' in response.status
    assert b'href="/create-ticket"' in response.data

def test_create_ticket_whitespace_assignment(create_ticket_with_invalid_data, auth_client: FlaskClient):
    response = create_ticket_with_invalid_data(assignment='      \t')

    with auth_client.session_transaction() as session:
        flashes = session['_flashes']
        assert len(flashes) == 1

        (category, message) = flashes[0]
        assert category == 'error'
        assert message == 'Could not submit ticket, assignment name must not be empty!'

    # Expect redirect back to create ticket page
    assert '302' in response.status
    assert b'href="/create-ticket"' in response.data

def test_create_ticket_whitespace_question(create_ticket_with_invalid_data, auth_client: FlaskClient):
    response = create_ticket_with_invalid_data(question='      \t')

    with auth_client.session_transaction() as session:
        flashes = session['_flashes']
        assert len(flashes) == 1

        (category, message) = flashes[0]
        assert category == 'error'
        assert message == 'Could not submit ticket, question must not be empty!'

    # Expect redirect back to create ticket page
    assert '302' in response.status
    assert b'href="/create-ticket"' in response.data

def test_create_ticket_invalid_mode(create_ticket_with_invalid_data, auth_client: FlaskClient):
    response = create_ticket_with_invalid_data(mode='invalid')

    with auth_client.session_transaction() as session:
        flashes = session['_flashes']
        assert len(flashes) == 1

        (category, message) = flashes[0]
        assert category == 'error'
        assert message == 'Could not submit ticket, must select a valid mode!'

    # Expect redirect back to create ticket page
    assert '302' in response.status
    assert b'href="/create-ticket"' in response.data
