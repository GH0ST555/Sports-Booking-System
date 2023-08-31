from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pytest
from app.models import UserAccount,Role,Facility,Activity,Sessions,Booking,Receipt
from app import app,db
from datetime import datetime, time, timedelta



@pytest.fixture(scope="module")
def test_app():
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SERVER_NAME": "localhost.localdomain:5000",
        "WTF_CSRF_ENABLED" : False,
    })
    with app.app_context():
        yield app

@pytest.fixture(scope="module")
def test_database(test_app):
    db.create_all()

    # Create test users
    user = UserAccount(User="htooaung", Email="test@gmail.com", Password="123", Mobile="+447760110194")
    employee = UserAccount(User="employee", Email="testemp@gmail.com", Password="123", Mobile="+447760110194")
    manager = UserAccount(User="manager", Email="testmgr@gmail.com", Password="123", Mobile="+447760110194")
    role_user = Role(name="User")
    role_employee = Role(name="Employee")
    role_manager = Role(name="Manager")
    db.session.add(role_user)
    db.session.add(role_employee)
    db.session.add(role_manager)

    db.session.add(user)
    db.session.add(employee)
    db.session.add(manager)

    facility = Facility(Name="Test Facility", Capacity=100, Start_Facility="00:00:00", End_Facility="23:59:59")
    db.session.add(facility)

    facility1 = Facility(Name="Test Facility 2", Capacity=100, Start_Facility="00:00:00", End_Facility="23:59:59")
    db.session.add(facility1)

    session = Sessions(Date=datetime.now().date(), Start_time=datetime.now().time(), End_time=(datetime.now() + timedelta(hours=1)).time(), Remaining_Cap=50, facility_id=facility.id)
    db.session.add(session)

    activity = Activity(Activity_Name="Test Activity", Amount=10)
    activity.facility_id = 1
    db.session.add(activity)


    activity1 = Activity(Activity_Name="Test Activity 2", Amount=10)
    activity1.facility_id = 2
    db.session.add(activity1)

    booking = Booking(user_id=1, session_id=session.id, activity_id=activity.id, Book_Time=datetime.now().date(), Status="Saved", Size=2, Amount=20)
    booking2 = Booking(user_id=1, session_id=session.id, activity_id=activity1.id, Book_Time=datetime.now().date(), Status="Saved", Size=2, Amount=20)
    db.session.add(booking)
    db.session.add(booking2)

    db.session.commit()

    yield db

    db.session.delete(user)
    db.session.delete(employee)
    db.session.delete(manager)
    db.session.delete(facility)
    db.session.delete(session)
    db.session.delete(activity)
    db.session.delete(booking)

    db.session.commit()

    db.drop_all()
