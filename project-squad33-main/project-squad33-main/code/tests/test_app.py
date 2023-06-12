import os
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import UserAccount,Role,Facility,Activity,Sessions,Booking,Receipt
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pytest
from flask import render_template, flash,redirect,request,make_response,url_for,current_app
from app import app,db
from twilio.base.exceptions import TwilioRestException, TwilioException
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta



def login_user(client, username, password):
    response = client.post('/login', data={
        'userName': username,
        'userPassword': password,
        'remember': False
    }, follow_redirects=True)
    assert response.status_code == 200
    return client

def login_employee(client, username, password):
    response = client.post('/emp_login', data={
        'userName': username,
        'userPassword': password,
        'remember': False
    }, follow_redirects=True)
    assert response.status_code == 200
    return client

def test_post_for_user(test_app, test_database):
    client = test_app.test_client()
    print(UserAccount.query.all())
    response = client.post('/create_account', data={
        "userName": "htooaungpost",
        "userEmail": "testhtooaung07@gmail.com",
        "userPassword": "Htoo123@",
        "userVerifyPassword": "Htoo123@",
        "CountryCode": "+44",
        "Mobile": "44776010914"
    }, follow_redirects=True)
    print(UserAccount.query.all())
    user = UserAccount.query.filter_by(User = "htooaungpost").first()
    assert user is not None
    assert response.status_code == 200

def test_user(test_app, test_database):
    user = UserAccount.query.filter_by(User="htooaung").first()
    assert user.User == "htooaung"
    assert user.Email == "test@gmail.com"
    assert user.Email != "htootayzaaung.01@gmailbbv.com"
    rl = Role.query.filter_by(name="User").first()
    user.roles.append(rl)
    assert user.check_password("123") == True
    assert user.roles == [rl]

def test_emp(test_app, test_database):
    user = UserAccount.query.filter_by(User="employee").first()
    assert user.User == "employee"
    assert user.Email == "testemp@gmail.com"
    assert user.Email != "htootayzaaung.01@gmailbbv.com"
    rl = Role.query.filter_by(name="Employee").first()
    user.roles.append(rl)
    assert user.check_password("123") == True
    assert user.roles == [rl]

def test_mgr(test_app, test_database):
    user = UserAccount.query.filter_by(User="manager").first()
    assert user.User == "manager"
    assert user.Email == "testmgr@gmail.com"
    assert user.Email != "htootayzaaung.01@gmailbbv.com"
    rl = Role.query.filter_by(name="Manager").first()
    user.roles.append(rl)
    assert user.check_password("123") == True
    assert user.roles == [rl]


def test_standard_routes(test_app):
    client = test_app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    response = client.get('/login')
    assert response.status_code == 200
    response = client.get('/create_account')
    assert response.status_code == 200
    response = client.get('/ec')
    assert response.status_code == 200
    response = client.get('/2FA')
    assert response.status_code == 200
    response = client.get('/reset')
    assert response.status_code == 200


def test_login_manager_protected_routes(test_app):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")

    # Test accessing protected pages
    response = logged_in_client.get('/mgr_homepage')
    assert response.status_code == 200
    response = logged_in_client.get('/analytics')
    assert response.status_code == 200

    response = logged_in_client.get('/create_emp')
    assert response.status_code == 200

    response = logged_in_client.get('/create_emp')
    assert response.status_code == 200


def test_create_employee_accounts(test_app,test_database):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")
    
    response = logged_in_client.post('/create_emp', data={
        "userName": "testemp",
        "userEmail": "emp007@gmail.com",
        "userPassword": "Emp1235@",
        "userVerifyPassword": "Emp1235@",
        "CountryCode": "+44",
        "Mobile": "776010914",
        "role" : "Employee"
    }, follow_redirects=True)
    user = UserAccount.query.filter_by(User = "testemp").first()
    assert user is not None
    assert response.status_code == 200
    db.session.delete(user)
    db.session.commit()

def test_create_manager_accounts(test_app,test_database):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")
    
    response = logged_in_client.post('/create_emp', data={
        "userName": "testmgr",
        "userEmail": "mgr007@gmail.com",
        "userPassword": "Mgr1235@",
        "userVerifyPassword": "Mgr1235@",
        "CountryCode": "+44",
        "Mobile": "776010914",
        "role" : "Manager"
    }, follow_redirects=True)
    user = UserAccount.query.filter_by(User = "testmgr").first()
    assert user is not None
    assert response.status_code == 200
    db.session.delete(user)
    db.session.commit()

def test_create_facility(test_app,test_database):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")
    response = logged_in_client.post('/create_facility', data={
        "Name": "TestFacility",
        "Capacity": 30,
        "Start_time": "8:00",
        "End_time": "20:00",
        "Amount": 20,
    }, follow_redirects=True)
    assert response.status_code == 200
    facility = Facility.query.filter_by(Name = "TestFacility").first()
    assert facility is not None


def test_update_user(test_app, test_database):
    client = test_app.test_client()
    logged_in_client = login_user(client, "htooaung", "123")
    response = logged_in_client.get('/update_user')
    assert response.status_code == 302
    response = logged_in_client.post('/update_user', data={
        'User': 'htooaung123',
        'password': '123456',
        'confirm_password': '123456',
        'email': 'new_email@example.com',
        'mobile': '+4434567890'
    }, follow_redirects=True)
    assert response.status_code == 200


##WORKS BUT COMMENTED TO REDUCE CHARGES FROM TWILIO
def test_2fa_post_request(test_app, test_database):
    client = test_app.test_client()
    logged_in_client = login_user(client, "htooaung", "123")
    form_data = {
        'email': 'user@example.com',
        'CountryCode': '+44',
        'pno': '7760110914'
    }
    response = logged_in_client.post('/2FA', data=form_data)
    assert response.status_code == 302




def test_invalid_number_2FA_request(test_app, test_database):
    client = test_app.test_client()
    logged_in_client = login_user(client, "htooaung", "123")
    form_data = {
        'email': 'user@example.com',
        'CountryCode': '+44',
        'pno': '123-456-7890'  
    }

    response = logged_in_client.post('/2FA', data=form_data)
    assert response.status_code == 302


def test_forget_password(test_app, test_database):
    client = test_app.test_client()
    logged_in_client = login_user(client, "htooaung", "123")
    form_data = {
        'userEmail': 'testmgr@gmail.com',
    }

    response = logged_in_client.post('/reset', data=form_data)
    assert response.status_code == 302

def test_forget_password_invalid_info(test_app, test_database):
    client = test_app.test_client()
    logged_in_client = login_user(client, "htooaung", "123")
    form_data = {
        'userEmail': 'ghost555@gmail.com',
    }

    response = logged_in_client.post('/reset', data=form_data)
    assert response.status_code == 200


def test_preset_booking(test_app, test_database):
    client = test_app.test_client()
    logged_in_client = login_user(client, "htooaung", "123")
    user = UserAccount.query.filter_by(User='htooaung').first()
    booking = Booking.query.filter_by(user_id=user.id).first()
    assert booking is not None
    assert booking.Status == "Saved"


def test_successful_booking(test_app, test_database):
    client = test_app.test_client()
    logged_in_client = login_user(client, "htooaung", "123")
    response = logged_in_client.get('/payment_success', follow_redirects=True)
    assert response.status_code == 200



def test_get_facility_data(test_app):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")
    response = logged_in_client.get('/facility_data/1')
    assert response.status_code == 200
    assert response.json == {
        'name': 'Test Facility',
        'capacity': 100,
        'start_time': '00:00:00',
        'end_time': '23:59:59'
    }

def invalid_get_facility_data(test_app):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")
    response = logged_in_client.get('/facility_data/500000')
    assert response.status_code == 200
    assert response.json == {
        'error': 'Facility not found'
    }

def test_get_activity_data(test_app):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")
    response = logged_in_client.get('/activity_data/1')
    assert response.status_code == 200
    assert response.json == {
        'name': 'Test Activity',
        'amount': 10,
        'facility_id': 1,
    }

def test_get_invalid_activity_data(test_app):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")
    response = logged_in_client.get('/activity_data/50000')
    assert response.status_code == 200
    assert response.json == {
        'error': 'Activity not found'
    }


def test_get_activity_linked_to_facility(test_app):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "employee", "123")
    response = logged_in_client.get('/get_activities/1')
    assert response.status_code == 200
    assert response.json == [{'Activity_Name': 'Test Activity', 'Amount': 10, 'facility_id': 1, 'id': 1}]

def test_delete_booking(test_app, test_database):
    client = test_app.test_client()
    logged_in_client = login_user(client, "htooaung", "123")
    response = logged_in_client.get('/delete_booking/1',follow_redirects=True)
    booking = Booking.query.all()
    assert response.status_code == 200



def test_create_activity(test_app,test_database):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")
    facility = Facility.query.filter_by(Name = "TestFacility").first()
    response = logged_in_client.post('/create_activity', data={
        "Activity_Name": "TestActivity",
        "Amount": 30,
        "Facility_Name": facility.id,
    }, follow_redirects=True)
    assert response.status_code == 200
    activity = Activity.query.filter_by(Activity_Name = "TestActivity").first()
    assert activity is not None

def test_user_membership_cancellation(test_app, test_database):
    client = test_app.test_client()
    user = UserAccount.query.filter_by(User="htooaung").first()
    user.Member = True
    db.session.commit()
    assert user.Member == True
    logged_in_client = login_employee(client, "employee", "123")
    response = logged_in_client.post(url_for('cancel_membership',user_id = user.id),follow_redirects = True)
    assert response.status_code == 200
    assert user.Member == False



def test_user_yearly_membership(test_app, test_database):
    client = test_app.test_client()
    response = client.post('/create_account', data={
        "userName": "new_user",
        "userEmail": "heehetest@gmail.com",
        "userPassword": "123",
        "userVerifyPassword": "123",
        "CountryCode": "+44",
        "Mobile": "44776010914"
    }, follow_redirects=True)
    new_user=UserAccount.query.filter_by(User="new_user").first()
    new_user.verified=True
    role = Role.query.filter_by(name="User").first()
    new_user.roles.append(role)
    db.session.commit()  
    assert new_user.Member == False    
    logged_in_client = login_user(client, "new_user", "123")
    response = logged_in_client.get('/success?payment_type=subscription&username=new_user&plan_id=yearly')
    updated_user = UserAccount.query.filter_by(User='new_user').first()
    assert updated_user.Member == True
    assert updated_user.start_date == datetime.utcnow().date()
    assert updated_user.end_date == datetime.utcnow().date() + relativedelta(years=1)   
    logged_in_client.post(url_for('cancel_membership',user_id = new_user.id),follow_redirects = True)


def test_user_monthly_membership(test_app, test_database):
    client = test_app.test_client()
    response = client.post('/create_account', data={
        "userName": "new_user_monthly",
        "userEmail": "heeheeetest@gmail.com",
        "userPassword": "123",
        "userVerifyPassword": "123",
        "CountryCode": "+44",
        "Mobile": "44776010914"
    }, follow_redirects=True)
    new_user=UserAccount.query.filter_by(User="new_user_monthly").first()
    role = Role.query.filter_by(name="User").first()
    new_user.verified=True
    new_user.roles.append(role)
    db.session.commit()  
    assert new_user.Member == False    
    logged_in_client = login_user(client, "new_user_monthly", "123")
    response = logged_in_client.get('/success?payment_type=subscription&username=new_user&plan_id=monthly')
    updated_user = UserAccount.query.filter_by(User='new_user').first()
    assert updated_user.Member == True
    assert updated_user.start_date == datetime.utcnow().date()
    assert updated_user.end_date == datetime.utcnow().date() + relativedelta(months=1)   
    logged_in_client.post(url_for('cancel_membership',user_id = new_user.id),follow_redirects = True)


def test_booking_success(test_app, test_database):
    client = test_app.test_client()
    logged_in_client = login_user(client, "htooaung", "123")
    response = client.get('/success?payment_type=booking&booking_id=2')
    booking = Booking.query.filter_by(id=2).first()
    assert response.status_code == 302
    assert booking.Status == 'Paid'


def test_update_facility(test_app, test_database):
    # Log in as a manager
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")

    # Create a new facility to modify
    logged_in_client.post(url_for('new_facility'), data={
        'Name': 'Test Facility',
        'Capacity': 10,
        'Start_time': '09:00',
        'End_time': '10:00',
        'Amount': 50,
    }, follow_redirects=True)

    # Send a POST request to update the facility
    facilities = Facility.query.all()
    facility_choices = [(f.id, f.Name) for f in facilities]
    facility_id = facility_choices[0][0]
    response = logged_in_client.post(url_for('update_facility'), data={
        'Facility_Namez': facility_id,
        'Name': 'New Facility Name',
        'Capacity': 20,
        'Start_time': '10:00',
        'End_time': '11:00',
    }, follow_redirects=True)

    # Check that the facility was updated correctly in the database
    updated_facility = Facility.query.filter_by(id=facility_id).first()
    assert updated_facility.Name == 'New Facility Name'
    assert updated_facility.Capacity == 20
    assert updated_facility.Start_Facility == '10:00'
    assert updated_facility.End_Facility == '11:00'


def test_update_activity(test_app, test_database):
    client = test_app.test_client()
    logged_in_client = login_employee(client, "manager", "123")
    activity = Activity.query.filter_by(Activity_Name="Test Activity").first()
    response = logged_in_client.post(url_for('update_activity'), data={
        'Activity_Selector': activity.id,
        'New_Activity_Name': 'Updated Activity',
        'New_Amount': 50,
        'New_Facility_Name': '1',
    }, follow_redirects=True)
    updated_activity = Activity.query.filter_by(id=activity.id).first()
    assert updated_activity.Activity_Name == 'Updated Activity'
    assert updated_activity.Amount == 50


def test_book_session_emp(test_app, test_database):
    # Create a user to book the session
    user = UserAccount(User="test_user", Email="test_user@example.com", Password="password", Mobile="555-555-5555")
    db.session.add(user)
    db.session.commit()

    # Create an activity and a session for the booking
    activity = Activity(Activity_Name="Test Activity", Amount=10)
    db.session.add(activity)
    db.session.commit()
    addsession = Sessions(
        facility_id=1,
        Date=datetime.now().date(),
        Start_time=datetime.now().time(),
        End_time=(datetime.now() + timedelta(hours=1)).time(),
        Remaining_Cap=10
    )
    addsession.activities.append(activity)
    db.session.add(addsession)
    db.session.commit()

    # Log in as the user
    client = test_app.test_client()
    logged_in_client = login_employee(client, "employee", "123")

    # Send a POST request to book the session
    response = logged_in_client.post('/book_session_emp?activity_id={}&group_size=3&activity_price=10'.format(str(activity.id)), data={
        'user_id': user.id,
        'session_id': addsession.id
    }, follow_redirects=True)


    assert addsession.Remaining_Cap == 7

    # Check that the booking was added to the database
    booking = Booking.query.filter_by(user_id=1,session_id=addsession.id).first()
    assert booking.user_id == 1
    assert booking.session_id == addsession.id
    assert booking.activity_id == activity.id
    assert booking.Size == 3
    assert booking.Amount == 30
    assert booking.Status == "Saved"
    assert booking.Book_Time == datetime.utcnow().date()

