#Relevant modules for the project.
from flask import Flask, render_template, flash,redirect,request,make_response,url_for,current_app, abort,session,jsonify
from app import app , models,db,admin,login_manager,mail
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from .forms import LoginForm,SignupForm,Auth2FaForm,Verify2FA,EmpLoginForm,EmpSignupForm,ForgetPassword,FacilityActivityForm,CreateFacilityForm,CreateActivityForm,UpdateActivityForm,UpdateFacilityForm,ResetPassword,ViewBookings,EditBookingForm, UpdateUserForm,UserMember,CreateBookings,BookingDetailsForm,RefundForm,ContactUsForm
from .models import UserAccount, Role, Booking, Facility, Receipt, Sessions,Activity, session_activity_association
from functools import wraps
from flask_login import LoginManager,login_required,logout_user,login_user,current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from twilio.rest import Client,TwilioException
from twilio.base.exceptions import TwilioRestException, TwilioException

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import URLSafeTimedSerializer
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import requests
import os
import pathlib
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from add_dynamic import dynamic_sessions,append_to_session
from datetime import datetime
import stripe
from collections import defaultdict
from sqlalchemy import desc, extract
from sqlalchemy.sql import func
import phonenumbers
from phonenumbers import NumberParseException
from flask import make_response
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from reportlab.platypus import Image


#Setup for twilio and Google SSO.
client = Client('AC6ad80acd35f02624971ed118dbc6ee3f', '75edf39774229fd85fd949e357190863')
GOOGLE_CLIENT_ID = '907426758204-iag4jlaj2j25u5cakobi2dual5806gn7.apps.googleusercontent.com'
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)

# Loads the required Role
#Redirects user to homepage if they access restricted content.
def require_role(role):
    """make sure user has this role"""
    def decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            if not current_user.has_role(role):
                return redirect("/")
            else:
                return func(*args, **kwargs)
        return wrapped_function
    return decorator

#method to validate phone numbers. Helps reduce Twilio Errors.
def is_valid_phone_number(number):
    try:
        parsed_number = phonenumbers.parse(number, None)
        return phonenumbers.is_valid_number(parsed_number)
    except phonenumbers.NumberParseException:
        return False


#************************* Admin View ******************************************
#Disabled For Submission.
# admin.add_view(ModelView(UserAccount, db.session))
# admin.add_view(ModelView(Role, db.session))
# admin.add_view(ModelView(Facility, db.session))
# admin.add_view(ModelView(Activity, db.session))
# admin.add_view(ModelView(Sessions, db.session))
# admin.add_view(ModelView(Booking, db.session))
# admin.add_view(ModelView(Receipt, db.session))

#**************************** HomePage *************************************************

#Route for the homepage
#Also handles the Contact us Info by sending users verification emails on submission.
@app.route('/', methods=['GET','POST'])
def Homepage():
    form = ContactUsForm()
    if request.method == 'POST':
        if form.validate() == False:
            flash('All fields are required.')
            return render_template('homepage.html', form=form)
        else:
            subject = 'Message Recieved'

            body = render_template('contact_us_email.html', user_email = form.email.data)
            message = Message(subject, recipients=[form.email.data], html=body,sender = 'arjun.krishnan0033@gmail.com')

            mail.send(message)
            return redirect('/')
    elif request.method == 'GET':
        return render_template('homepage.html', title='HomePage',form = form)


#Getter to get the information of upcoming activites using facility id.
@app.route('/facility/<int:facility_id>/activities')
def get_upcomming_activities(facility_id):
    activities = Activity.query.filter_by(facility_id=facility_id).all()
    return jsonify([activity.activity_to_dict() for activity in activities])


#**** User Create Account and Login: Reset Password, 2FA & Google Login ***********************

#******************* Route for Login ****************************************

#Handles user authentication and checks if the account has the 'User' role
#If the user logs in but has the wrong role, It results in user being redirected to homepage
#On successful login it redirects to user page
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = UserAccount.query.filter_by(User=form.userName.data).first()
        if user is None or not user.check_password(form.userPassword.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        if not user.verified:
            flash('Please verify your email before logging in.')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember.data)
        if user.has_role("User"):
            return redirect("/user")
        else:
            return redirect('/')
    return render_template('login_page.html', title='Login', form=form)

#******************* Route for Create Account ****************************************
#Creates a user account.
#Checks if the username and email already exists, preventing duplicate information from being used.
#On success the user account is created and user activiation process begins
#Else page is reloaded.
@app.route('/create_account', methods=['GET','POST'])
def signup():
    form = SignupForm()
    user_name = form.userName.data
    user_email = form.userEmail.data
    user_password = form.userPassword.data
    user_Role = Role.query.filter_by(name="User").first() 
    user_number = form.Mobile.data

    if form.validate_on_submit():
        user_n = UserAccount.query.filter_by(User=user_name).first()
        user_e = UserAccount.query.filter_by(Email=user_email).first()
        if user_n is not None:
            flash('User already exists')
            app.logger.error('Error: Create Account Failed')
            return redirect('/create_account')
        if user_e is not None:
            flash('email ID already exists')
            app.logger.error('Error: Create Account Failed')
            return redirect('/create_account')
        userData = UserAccount(User=user_name, Email=user_email, Password=form.userPassword.data,Mobile = form.CountryCode.data+form.Mobile.data)
        userData.roles.append(user_Role)
        verification_token = generate_verification_token(user_email)
        userData.verification_token = verification_token 
        db.session.add(userData)
        db.session.commit()

        return redirect(url_for('send_verification_email', user_email=user_email, verification_token=verification_token))
    return render_template('signup.html', title='signup', form=form)

#******************* Route for Login with Phone ****************************************

#Route to handle Two-Factor authentication.
#validate mobile number information.
#if mobile is validated verification token is generated by twilio.
#If numnber is not validated, error message is displayed.
@app.route('/2FA', methods=['GET', 'POST'])
def Auth2Fa():
    f1 = Auth2FaForm()
    email = f1.email.data
    userAcc = UserAccount.query.filter_by(Email=email).first()

    if f1.validate_on_submit():
        print(f1.CountryCode.data)
        mob = f1.CountryCode.data + str(f1.pno.data)

        # Validate the phone number
        if is_valid_phone_number(mob):
            request_verification_token(mob)
            return redirect(url_for('ec', mob=mob, email=email))
        else:
            flash('Invalid phone number format. Please enter a valid number.', 'error')


    return render_template('login2fa.html', title='2FA', form=f1)

#Route to verify the generated code is entered.
#Twilio checks if the token is correct.
#If correct the user logs in.
@app.route('/ec', methods=['GET', 'POST'])
def ec():
    mobil = request.args.get('mob')
    print(mobil)
    eml = request.args.get('email')
    f2 = Verify2FA()
    tok = f2.token.data
    userAcc = UserAccount.query.filter_by(Email=eml).first()
    if request.method == 'POST':
        login = check_verification_token(mobil, tok)
        print("Verification check result:", login)
        if login == True:
            login_user(userAcc)
            return redirect('/user')
    return render_template('verify.html', title='2FA', form2=f2)


#Method to generate the verification token for email validation
def generate_verification_token(user_email):
    s = Serializer(current_app.config['SECRET_KEY'])
    return s.dumps({'email': user_email}).decode('utf-8')

#Twilio method to check verification toekn.
#If Handles any exceptions raised by twilio for errors.
def check_verification_token(phone, token):
    print("Phone:", phone)
    print("Token:", token)
    verify = client.verify.services('VA3aca3bf651a0ca9bcb349309b4737dc4')
    try:
        result = verify.verification_checks.create(to=phone, code=token)
    except TwilioException as e:
        print("Twilio exception:", e)
        return False
    return True

#Twilio method to generate token given the users mobile number.
#Handles Any exceptions by twilio. Preventing user login if False is returned.
def request_verification_token(phone):
    verify = client.verify.services('VA3aca3bf651a0ca9bcb349309b4737dc4')
    try:
        verify.verifications.create(to=phone, channel='sms')
    except TwilioException:
       return False


#******************* Sending Account Verification Link ****************************************
@app.route('/send-verification-email')
def send_verification_email():
    # Get the current user's email and verification token
    user_email = request.args.get('user_email')
    verification_token = request.args.get('verification_token')

    # Generate the verification URL using Flask-URL-Generator
    verification_url = url_for('verify_email', token = verification_token, _external=True)
    flash('The verification link is sent to your email address.')
    # Create the email message
    subject = 'Verify Your Email'

    body = render_template('send_verify_email.html', verification_url=verification_url)
    message = Message(subject, recipients=[user_email], html=body,sender = 'arjun.krishnan0033@gmail.com')

    mail.send(message)

    # Return a message to the user
    flash('A verification email has been sent to your email address.')
    return redirect(url_for('login'))

@app.route('/verify-email/<token>')
def verify_email(token):
    # Find the user with the given verification token
    user = UserAccount.query.filter_by(verification_token=token).first()

    if user:
        # Verify the user's email and remove the verification token
        user.verified = True
        user.verification_token = None
        db.session.commit()
        # Return a message to the user
        flash('Your email has been verified.')
        msg = Message('Account Created', sender = 'arjun.krishnan0033@gmail.com', recipients = [user.Email])
        msg.html = render_template('mail.html', User=user.User)     #
        mail.send(msg)
    else:
        # Return a message to the user
        flash('The verification link is invalid.')

    return redirect(url_for('login'))

#******************* Resetting Password ****************************************

# Route for resetting the password

@app.route('/reset', methods=["GET", "POST"])
def reset():
    form = ForgetPassword()
    user_email = form.userEmail.data
    if form.validate_on_submit():
        user = UserAccount.query.filter_by(Email=form.userEmail.data).first()

        if user:
            # Generate a token that is valid for 1 hour
            s = Serializer(current_app.config['SECRET_KEY'])
            token = s.dumps(user_email, salt='recover-key')
            
            # Construct the password reset link
            reset_url = url_for('reset_password', token=token, _external=True)

            # Send an email to the user with the password reset link
            subject = 'Password reset request'

            body = render_template('password_reset_email.html', reset_url=reset_url, user_email = user_email)
            message = Message(subject, recipients=[user_email], html=body,sender = 'arjun.krishnan0033@gmail.com')

            mail.send(message)

            flash('An email has been sent with instructions to reset your password', 'success')
            return redirect(url_for('login'))

        flash('Email address not found', 'danger')

    return render_template('recover.html', title='Reset Password', form=form)

#route to validate the reset password.
#Only allows password to be reset if the toek is validate.
#Chceks if the user email also exists before resetting the password.
#If all checks are passed. User password is reset with success prompt.
@app.route('/reset_password/<token>', methods=["GET", "POST"])
def reset_password(token):
    try:
        s = Serializer(current_app.config['SECRET_KEY'])
        email = s.loads(token, salt='recover-key')
    except:
        flash('The password reset link is invalid or has expired', 'danger')
        return redirect(url_for('reset'))

    user = UserAccount.query.filter_by(Email=email).first()
    if not user:
        flash('Email address not found', 'danger')
        return redirect(url_for('reset'))

    form = ResetPassword()
    if form.validate_on_submit():
        user.Password= generate_password_hash(form.userPassword.data)
        db.session.commit()
        flash('Your password has been reset', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', title='Reset Password', form=form)

# Route for Login with Google Account

@app.route("/google_login")
def google_login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)
    if not session["state"] == request.args["state"]:
        abort(500)
    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    google_id = id_info.get("sub")
    email = id_info.get("email")

    # Check if the user's email exists in the database
    user = UserAccount.query.filter_by(Email=email).first()
    if user:
        session["google_id"] = google_id
        session["email"] = email
        login_user(user)
        print("Success")
        return redirect("/user")
    else:
        # Redirect the user to an unauthorized page
        print("Failed!")
        flash('Invalid Credentials')
        return redirect("/login")


@app.route("/protected_area")
@login_required
def protected_area():
    return f"Hello {session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"

#********************************* Route to Redirect User After they Login ************************

#User homepage
@app.route('/user', methods=['GET','POST'])
@login_required
@require_role(role="User")
def user():
    return render_template('user.html',title= 'User', User = current_user)

#Flask defualt logout handler.
@app.route("/logout")
@login_required
def logout():
    for key in list(session.keys()):
        session.pop(key)
    logout_user()
    return redirect('/')

#************** End of User Login, Creat Account: Reset, 2FA, Google Login, Logout *******************

# ***************************************** Stripe Payment ************************************


@app.route('/all_products')
def all_products():
    return render_template('all_products.html', products=products)

#Stripe checkout session for memberships/bookings created by user.
#Displays price in GBP
#Currently Stripe is set to Test Mode but can be easily switched to Accomadate Real Payments.
@app.route('/order_products', methods=['GET','POST'])
@login_required
def order_products():
    total_amount = float(request.args.get('total_amount'))

    total_amount_cents = int(total_amount * 100)

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "gbp",
                    "product_data": {
                        "name": "Total Booking Amount",
                    },
                    "unit_amount": total_amount_cents,
                },
                "quantity": 1,
            },
        ],
        mode="payment",
        success_url=request.host_url + 'payment_success',
        cancel_url=request.host_url + "Homepage",
    )

    return redirect(checkout_session.url)



#******************************* When User Purchases Membership ************************

#Membership Prices For Monthly and annual memberships.
plans = {
    'monthly': {
        'name': 'Monthly Membership',
        'price_id': 'price_1MmhrZBqkMuCWI2NYyG9Ye7N',
        'interval': 'month',
        'currency': 'gbp'
    },
    'yearly': {
        'name': 'Yearly Membership',
        'price_id': 'price_1MmhqtBqkMuCWI2NEADoQBHn',
        'interval': 'year',
        'currency': 'gbp'
    }
}

#Route to handle the user orders.
#Users can cancel their orders redirecting them to cancel page.
#Else to the success url which activates user membership.
@app.route('/order_subscription/<string:username>', methods=['GET', 'POST'])
def order_subscription(username):
    user = UserAccount.query.filter_by(User=username).first()

    if user is None:
        abort(404, f"No user found with username: {username}")

    if request.method == 'POST':
        plan_id = request.form.get('plan_id')

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": plans[plan_id]['price_id'],
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=request.host_url + f'success?payment_type=subscription&username={username}&plan_id={plan_id}',
            cancel_url=request.host_url + "cancel",
        )

        # Redirect the user to the Checkout page for the subscription
        return redirect(checkout_session.url)

    return render_template('all_subscriptions.html', username=username, plans=plans, current_user=user)

#Route to allow users to cancel their membership
#Cchecks if the user account exists and if the user is a member before cancelling.
#If user is not member the user is redirected to homepage
#If user is a member the membership is revoked and memebrship information is erased.
@app.route('/cancel_usermembership/<int:user_id>', methods=['POST'])
@require_role(role="User")
@login_required
def cancel_usermembership(user_id):
    user = UserAccount.query.filter_by(id = user_id).first()
    print(user)
    if user:
        user.Member = False
        user.Membership_Type = None
        user.start_date = None
        user.end_date = None
        db.session.commit()
        flash('Membership canceled successfully')
        return redirect(url_for('user'))
    else:
        flash('User not found')
        return redirect(url_for('user'))

#******************************* When User Purchases Membership ************************ 

@login_required
#route to handle the successful payment 
#Makes the user a member and sets info based on the length of the subscription.
@app.route('/success')
def success():
    payment_type = request.args.get('payment_type')

    if payment_type == 'booking':
        booking_id = request.args.get('booking_id')
        booking = Booking.query.get(booking_id)
        if booking:
            booking.Status = "Paid"
            db.session.commit()

    elif payment_type == 'subscription':
        username = request.args.get('username')
        user = UserAccount.query.filter_by(User=username).first()
        if user:
            plan_id = request.args.get('plan_id')
            plan = plans.get(plan_id)

            if plan:
                # Set membership start and end dates based on the subscription plan
                start_date = datetime.utcnow().date()
                if plan['interval'] == 'month':
                    end_date = start_date + relativedelta(months=1)
                elif plan['interval'] == 'year':
                    end_date = start_date + relativedelta(years=1)
                else: 
                    end_date = None

                # Update the user's membership information in the database
                user.Member = True
                user.start_date = start_date
                user.end_date = end_date
                user.Membership_Type = plan['name']
                db.session.commit()

    return redirect(url_for('user'))





#******************************* When User Purchases any activity ************************

from datetime import datetime

#Handles success for user bookings.
#Sets the booking status form 'Saved' to 'Paid'.
#Recipt is now generated and a pdf version is sent to the users Email.
@app.route('/payment_success', methods=['GET'])
@login_required
def payment_success():
    user_bookings = Booking.query.filter_by(user_id=current_user.id, Status="Saved").all()

    if not user_bookings:
        flash('No bookings found with the "Saved" status. Please try again.')
        return redirect(url_for('my_bookings'))

    total_amount = sum([booking.Size * booking.activity.Amount for booking in user_bookings])

    new_receipt = Receipt(
        user_id=current_user.id,
        Amount=total_amount
    )

    db.session.add(new_receipt)
    db.session.commit()
    receipt_id = new_receipt.id

    for booking in user_bookings:
        booking.Status = 'Booked'
        booking.receipt_id = receipt_id

    db.session.commit()
    flash('Payment successful! Your booking statuses have been updated to "Booked".')

    static_folder = os.path.join(app.root_path, 'static')
    image_path = os.path.join(static_folder, 'images', 'logo_black.png')
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    x = 200
    y = 610

    img = Image(image_path)
    img.drawOn(p, x, y)

    p.drawCentredString(300, 600, "-------Booking Receipt-------")
    p.drawCentredString(300, 550, f"Name: {current_user.User}")
    p.drawCentredString(300, 500, f"Date: {datetime.now().date()}")
    p.drawCentredString(300, 450, f"Time: {datetime.now().time()}")
    p.drawCentredString(300, 400, f"Amount: {total_amount}")
    # y -= 50
    # p.drawCentredString(300, y, "Booked Sessions:")
    #bookings = Booking.query.filter_by(user_id=current_user.id).all()
    receipt_bookings = Booking.query.filter_by(receipt_id=new_receipt.id).all()
    y = 400
    for booking in receipt_bookings:
        y -= 50
        facility_name = booking.session.facility.Name
        activity_name = booking.activity.Activity_Name
        session_start_time = booking.session.Start_time
        session_end_time = booking.session.End_time
        p.drawCentredString(300, y,f"Booking ID {booking.id}:Facility {facility_name},: Activity {activity_name}, Session start {session_start_time}, Session end {session_end_time}")


    #     y -= 20
    #     activites = Activity.query.filter_by(activity_id=bookings.activity_id).all()
    #     p.drawCentredString(300, y, activites.Activity_Name)

    
    p.save()
    buffer.seek(0)
    msg = Message('Booking Receipt', sender='your_email@example.com', recipients=[current_user.Email])
    msg.attach('receipt.pdf', 'application/pdf', buffer.read())
    mail.send(msg)

    return redirect(url_for('my_bookings'))

#***************************************** End of Stripe ********************************************

#**************************************** Manager Role **********************************************

#route for Employee & Manager login
#Redirects the user to Employee/Manager Homepage depending on the role of the account.
#PRecents login if account does not exist, Password is incorrect or if the account type is User.
@app.route('/emp_login', methods=['GET','POST'])
def employee_login():
    form = EmpLoginForm()
    usr = form.userName.data
    if form.validate_on_submit():
        user = UserAccount.query.filter_by(User=usr).first()
        if user is None or not user.check_password(form.userPassword.data):
            flash('Invalid Login')
            app.logger.warning('Invalid Login')
            return redirect('/emp_login')
        if not user.has_role("Employee") and not user.has_role("Manager"):
            app.logger.warning('Not an Employee')
            return redirect('/emp_login')
        if user.has_role("Employee"):
            login_user(user)
            return redirect("/emp_homepage")
        if user.has_role("Manager"):
            login_user(user)
            return redirect("/mgr_homepage")
    return render_template('emplogin_page.html',
                        title='Login',form = form)

#Manager Homepage
@app.route('/mgr_homepage')
@login_required
@require_role(role="Manager")
def MgrHomepage():
    #redirects user to landing page
    return render_template('yt.html',
                           title='Home',User = current_user)

#Route to handle Employee Creation.
#Employee/Manager accounts can be created.
#Route accessible by managers only as per spec
#Checks if the Email and username are existing, preventing account creation if so
#Else account is created, Bypassing verification process.
@app.route('/create_emp',methods=['GET','POST'])
@require_role(role="Manager")
@login_required
def newemp():
    form = EmpSignupForm()
    usr = form.userName.data
    email = form.userEmail.data
    paswrd = form.userPassword.data
    if form.validate_on_submit():
        usern = UserAccount.query.filter_by(User=usr).first()
        emailn = UserAccount.query.filter_by(Email=email).first()
        if usern is not None:
            flash('User already exists')
            app.logger.warning('Invalid Account Creation')
            return redirect('/create_emp')
        if emailn is not None:
            app.logger.warning('Invalid Account Creation')
            flash('email ID already exists')
            return redirect('/create_emp')
        userData = UserAccount(User=usr, Email=email, Password=form.userPassword.data,Mobile = form.CountryCode.data+form.Mobile.data)
        db.session.add(userData)
        role = Role.query.filter_by(name=form.role.data).first()
        userData.verified=True
        userData.roles.append(role)
        db.session.commit()
        return redirect('/mgr_homepage')
    #redirects user to landing page
    return render_template('newemp.html',title='Home',form = form)


#Route to handle Facility Creation.
#Facility with a default activity 'General Usr' is created
#Route accessible by managers only as per spec
#Checks if the Facility exists, preventing Facility creation if so
#If checks are passed, 2 Weeks worth of sessions is generated using the dynamic sessions script.
@app.route('/create_facility',methods=['GET','POST'])
@require_role(role="Manager")
@login_required
def new_facility():
    form = CreateFacilityForm()
    if form.validate_on_submit():
        checkfacility =Facility.query.filter_by(Name = form.Name.data).first()
        if checkfacility is not None:
            flash('Facility already exists')
            return redirect('/create_facility')
        facility = Facility(Name=form.Name.data, Capacity=form.Capacity.data, Start_Facility=form.Start_time.data, End_Facility=form.End_time.data)
        activity = Activity(Activity_Name="General use", Amount=form.Amount.data)
        db.session.add(activity)
        facility.activities.append(activity)
        db.session.add(facility)
        db.session.commit()
        dynamic_sessions(facility.id, form.Start_time.data, form.End_time.data, form.Capacity.data,activity.id)
        return redirect('/mgr_homepage')
    return render_template('createfacility.html',form=form)



#Route to handle Activity Creation.
#Activity with entered information is created
#Route accessible by managers only as per spec
#Checks if the Activity exists, preventing Activity creation if so
#If checks are passed, Activity is added to all existing sessions that have the same facility as this activity.
@app.route('/create_activity',methods=['GET','POST'])
@require_role(role="Manager")
@login_required
def new_activity():
    facilities = Facility.query.all()
    facility_choices = [(f.id, f.Name) for f in facilities]
    form = CreateActivityForm()
    form.Facility_Name.choices = facility_choices

    if form.validate_on_submit():
        facility = Facility.query.filter_by(id = form.Facility_Name.data).first()
        check_activity = Activity.query.filter_by(Activity_Name = form.Activity_Name.data , facility_id = form.Facility_Name.data).first()
        activity = Activity(Activity_Name=form.Activity_Name.data, Amount=form.Amount.data)
        if check_activity in facility.activities:
            flash('Activity already exists')
            return redirect('/create_activity')
        facility.activities.append(activity)
        db.session.add(activity)
        db.session.commit()
        append_to_session(facility.id,activity.id)
        return redirect('/mgr_homepage')
    return render_template('createactivity.html',form=form)


#Route to update activity information
#Route accessible to managers only as per spec
#Allows user to select the facility, then displays all activites linked to the facility in a select dropdown
#The activity information is then updated.
@app.route('/update_Activity',methods=['GET','POST'])
@require_role(role="Manager")
@login_required
def update_activity():
    facilities = Facility.query.all()
    facility_choices = [(f.id, f.Name) for f in facilities]

    activities = Activity.query.all()
    activity_choices = [(a.id, a.Activity_Name) for a in activities]

    form = UpdateActivityForm()
    form.New_Facility_Name.choices = facility_choices
    form.Activity_Selector.choices = activity_choices
    if request.method == "POST" and form.validate_on_submit():
        activity = Activity.query.filter_by(id=int(form.Activity_Selector.data)).first()
        activity.Activity_Name = form.New_Activity_Name.data
        activity.Amount = form.New_Amount.data
        # facilityz = Facility.query.filter_by(id = int(form.New_Facility_Name.data)).first()
        # activity.facility_id = facilityz.id
        db.session.commit()
        return redirect('/mgr_homepage')
    return render_template('updateactivity.html',form=form)

#Route to update facility information
#Route accessible to managers only as per spec
#Allows user to select the facility from the dropdown.
#The activity Facilty is then updated if form is valid.
@app.route('/update_facility',methods=['GET','POST'])
@require_role(role="Manager")
@login_required
def update_facility():
    form = UpdateFacilityForm()
    facilities = Facility.query.all()
    facility_choices = [(f.id, f.Name) for f in facilities]
    form = UpdateFacilityForm()
    form.Facility_Namez.choices = facility_choices
    
    if request.method == "POST" and form.validate_on_submit():
        
        facility = Facility.query.filter_by(id=int(form.Facility_Namez.data)).first()
        facility.Name = form.Name.data 
        facility.Capacity = form.Capacity.data
        facility.Start_Facility = form.Start_time.data
        facility.End_Facility = form.End_time.data
        db.session.commit()
        return redirect('/mgr_homepage')
    if not form.validate_on_submit():
        print(form.errors)
    return render_template('updatefacility.html',form=form)


#getter to get the facility information and converts data to JSON form.
@app.route('/facility_data/<string:facility_name>')
@require_role(role="Manager")
@login_required
def facility_data(facility_name):
    facility = Facility.query.filter_by(id=int(facility_name)).first()
    if not facility:
        return jsonify({'error': 'Facility not found'})
    data = {
        'name': facility.Name,
        'capacity': facility.Capacity,
        'start_time': facility.Start_Facility,
        'end_time': facility.End_Facility
    }

    return jsonify(data)


#getter to retrieve activity information and converts data to JSON form.
#requires the activity name as a string.
@app.route('/activity_data/<string:activity_name>')
@require_role(role="Manager")
@login_required
def activity_data(activity_name):
    activity = Activity.query.filter_by(id=int(activity_name)).first()
    if not activity:
        return jsonify({'error': 'Activity not found'})
    data = {
        'name': activity.Activity_Name,
        'amount': activity.Amount,
        'facility_id': activity.facility_id,
    }
    return jsonify(data)

#Getter to get facility and all activities linked to that facility
#Converts this data into JSON form
#Requires the facility id as a paramenter.
@app.route('/facility_activities/<int:facility_id>')
@require_role(role="Manager")
@login_required
def extractactivites(facility_id):
    facility = Facility.query.get_or_404(facility_id)
    activities = facility.activities.all()
    activity_names = [(activity.id, activity.Activity_Name) for activity in activities]
    return jsonify(activity_names)

#Page that lists all Facility Activity Prices
#This was impelemented to allow info to be viewed and updated
@app.route('/pricing', methods =["GET","POST"])
@require_role(role="Manager")
@login_required
def pricing():
    activity = Activity.query.all()
    return render_template('pricing.html', activity = activity)
#****************************************** End of Manager Roles *****************************************

#************************************ Employee Roles ********************************************

#Route for employee homepage
@app.route('/emp_homepage')
@require_role(role="Employee")
@login_required
def EmpHomepage():
    #redirects user to landing page
    return render_template('employeefp.html', title='Home',User = current_user)
 
#Rote that allows employees to amend bookings on behalf of the user.
#Validates the email entered exists.
#On success retrieves all the bookinngs which are Paid by the user.
#Only accessible by employees based on spec
@app.route('/lookup_bookings', methods=['GET', 'POST'])
@require_role(role="Employee")
@login_required
def look_bookings():
    form = ViewBookings()
    bookings = None
    form_submitted = None
    if request.method == 'POST' and form.validate_on_submit():
        form_submitted = True
        user_email = form.userEmail.data
        user = UserAccount.query.filter_by(Email = user_email).first()
        if user is not None:
            bookings = Booking.query.filter_by(user_id=user.id, Status="Booked").all()
        else:
            flash('User not found', 'danger')
    return render_template('view_bookingsEmp.html',bookings = bookings, form = form, form_submitted= form_submitted)

#Route which handle booking modification
#The booking id is taken in as a parameter.

@app.route('/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
@require_role(role="Employee")
@login_required
def edit_booking(booking_id):
    booking = Booking.query.get(booking_id)
    print(booking)  # Get the booking by its ID

    if not booking:
        flash('Booking not found', 'danger')
        return redirect(url_for('look_bookings'))

    if booking.Status != "Booked":
        flash('Booking cannot be edited because it has already occurred', 'danger')
        return redirect(url_for('look_bookings'))

    form = EditBookingForm(obj=booking)

    if request.method == 'POST' and form.validate_on_submit():
        if form.cancel.data:  # Check if the cancel button was clicked
            booking_sessionFilter = Sessions.query.filter_by(Start_time=form.start_time.data, End_time=form.end_time.data).first()
            print(booking_sessionFilter)
            booking_filter = Booking.query.filter_by(Book_Time = form.date.data,session = booking_sessionFilter.id).first()
            if not booking_filter and booking_sessionFilter:
                flash('No Booking Found to Cancel.')
            else:
                booking.Status = "Cancelled"
                booking.session.Remaining_Cap += booking.Size  # Increase the remaining capacity
                flash('Booking cancelled successfully', 'success')
        else:
            old_session = booking.session
            new_session = Sessions.query.filter_by(Date=form.date.data, Start_time=form.start_time.data, End_time=form.end_time.data).first()
            print(new_session)

            if not new_session:
                flash('No session found for the new date and time', 'danger')
                return render_template('edit_booking.html', form=form, booking_id=booking_id)

            if new_session.Remaining_Cap < booking.Size:
                flash('Not enough capacity for the new session', 'danger')
                return render_template('edit_booking.html', form=form, booking_id=booking_id)

            # Update the remaining capacities
            old_session.Remaining_Cap += booking.Size
            new_session.Remaining_Cap -= booking.Size

            # Update the booking
            booking.session_id = new_session.id
            booking.session = new_session
            db.session.add(old_session)
            db.session.add(new_session)
            flash('Booking updated successfully', 'success')

        db.session.commit()
        return redirect(url_for('look_bookings'))

    return render_template('edit_booking.html', form=form, booking_id=booking_id, booking = booking)

#Route that takes in the user account to check membership information
#Only allows member details to be accessed if the account is a User account
#Else respective errors are displayed
@app.route('/view_userMembership', methods=['GET', 'POST'])
@require_role(role="Employee")
@login_required
def create_userMembership():
    form = UserMember()
    form_submitted = False
    member = None
    if request.method == 'POST' and form.validate_on_submit():
        form_submitted = True
        user_email = form.userEmail.data

        isuser = UserAccount.query.filter_by(Email = user_email).all()

        if not isuser:
            flash('Not a User')
        
        else:
            verifyuser = UserAccount.query.filter_by(Email = user_email).first()

            if verifyuser.has_role("User"):
                ismember = UserAccount.query.filter_by(Email = user_email).first()
                if ismember.Member:
                    member = verifyuser
                else:
                    flash('Not a Member')
            else:
                flash('Not a User')
    return render_template('view_userMembership.html',form = form, form_submitted = form_submitted, member = member)


#route that cancels users membership
#Requires user id as a parameter.
#Deletes all membership information and revokes membership on successful identification of account
#Else error message is displayed.
@app.route('/cancel_membership/<int:user_id>', methods=['POST'])
@require_role(role="Employee")
@login_required
def cancel_membership(user_id):
    user = UserAccount.query.get(user_id)
    if user:
        user.Member = False
        user.Membership_Type = None
        user.start_date = None
        user.end_date = None
        db.session.commit()
        flash('Membership canceled successfully')
        return redirect(url_for('create_userMembership'))
    else:
        flash('User not found')
        return redirect(url_for('create_userMembership'))


#Route that creates bookings for a user by the employee
#Checks if the user account existis, returning appropriate error messages if account does not exist.
#IF account exists a booking can be made on behalf of the user
@app.route('/create_bookings', methods=['GET', 'POST'])
@require_role(role="Employee")
@login_required
def create_booking():
    form = CreateBookings()
    bookings = None
    form_submitted = None
    user = None
    if request.method == 'POST' and form.validate_on_submit():
        form_submitted = True
        user_email = form.userEmail.data

        isuser = UserAccount.query.filter_by(Email = user_email).all()

        if not isuser:
            flash('Not a User')
        
        else:
            verifyuser = UserAccount.query.filter_by(Email = user_email).first()

            if verifyuser.has_role("User"):
                bookings = UserAccount.query.filter_by(Email = user_email).all()
                flash('Not a User')
            else:
                flash('Not a User')

    return render_template('create_bookings.html',bookings = bookings, form = form, form_submitted= form_submitted)


#Route to handle the booking information
#Taking in facility and activity information, Date and party size to get the number of sessions that match the criteria.
@app.route('/booking_details', methods=['GET', 'POST'])
@login_required
@require_role(role="Employee")
def booking_details():
    form = BookingDetailsForm()
    sessions = None
    data = None  # Initialize selected_activity_id here
    user_id = request.args.get('user_id')
    print(user_id)
    form.facility.choices = [(facility.id, facility.Name) for facility in Facility.query.all()]
    form.activity.choices = [(activity.id, activity.Activity_Name) for activity in Activity.query.all()]

    group_size = None
    activity_price = None
    activity_id = None

    if request.method == 'POST':
        activity_id1 = form.activity.data
        print(activity_id1)
        data_price = Activity.query.filter_by(id = activity_id1).first()
        activity_price = int(data_price.Amount)
        group_size = int(form.capacity.data)
        print(activity_price)
        print(group_size)
        print("Form submitted")

        if form.validate_on_submit():
            facility_id = form.facility.data
            activity_id = form.activity.data
            date = form.date.data
            capacity = form.capacity.data

            data = Activity.query.filter_by(id = activity_id).first()
            venue = Facility.query.get(facility_id)

            if form.date.data == datetime.now().date():
                current_time = datetime.now().time()
                sessions = Sessions.query.filter(
                    Sessions.facility_id == facility_id,
                    Sessions.activities.any(id=activity_id),
                    Sessions.Date == form.date.data,
                    Sessions.Start_time >= current_time,
                    Sessions.Remaining_Cap >= capacity
                ).all()
            else:
                sessions = Sessions.query.filter(
                    Sessions.facility_id == facility_id,
                    Sessions.activities.any(id=activity_id),
                    Sessions.Date == form.date.data,
                    Sessions.Start_time >= venue.Start_Facility,
                    Sessions.Remaining_Cap >= capacity
                ).all()
        else:
            print("Form validation failed")
            print(form.errors)

    return render_template('booking_details.html', form=form, sessions=sessions,data = data,group_size=group_size,activity_price=activity_price,activity_id = activity_id,user_id = user_id)

#Gets all the information from the route above and displays all the possible sessions.
@app.route('/book_session_emp', methods=['POST'])
@login_required
# @require_role(role="User")
def book_session_emp():
    session_id = request.form.get('session_id')
    activity_id = int(request.args.get('activity_id'))
    user_id = int(request.form.get('user_id'))
    group_size = int(request.args.get('group_size'))
    activity_price = int(request.args.get('activity_price'))
    booking_Price = int(group_size * activity_price)
    session = Sessions.query.get(session_id)
    # Check if there's enough remaining capacity for the booking
    if session.Remaining_Cap >= group_size:
        booking = Booking(
            user_id =user_id,
            session_id=session_id,
            activity_id=activity_id,
            Book_Time = session.Date,
            Status="Saved",  
            Size=group_size,
            Amount = booking_Price
        )
        booking.user_id = 1

        # Reduce the session's remaining capacity by the group size
        session.Remaining_Cap -= group_size

        db.session.add(booking)
        db.session.commit()

        # Add a message to notify the user that the booking was successful.
        flash('Booking successful!')
    else:
        flash('Not enough remaining capacity for the booking.')

    return redirect(url_for('booking_details'))


#Getter that displays activity id and activity name for a given facility
#requires facility id as a parameter
@app.route('/get_activities/<facility_id>', methods=['GET'])
@login_required
@require_role(role="Employee")
def get_activities_createBooking(facility_id):
    facility = Facility.query.get(facility_id)
    activities = [{'id': activity.id, 'Name': activity.Name} for activity in facility.activities]
    return jsonify(activities)

#****************************************** End of Employee ******************************************************
@login_manager.user_loader
def load_user(id):
    return UserAccount.query.get(int(id))


#****************************************** User: After Login ******************************************************
#Route to allow users to select the activity , Facility ,Date and party size to 
@app.route('/lookup_venue', methods=['POST', 'GET'])
@login_required
@require_role(role="User")
def view_venue():
    form = FacilityActivityForm()

    form.facility_name.choices = [(facility.id, facility.Name) for facility in Facility.query.all()]
    form.activity_name.choices = [(activity.id, activity.Activity_Name) for activity in Activity.query.all()]

    # Update the activity_name choices here
    all_activities = Activity.query.all()
    # form.activity_name.choices = [(a.Activity_Name, a.Activity_Name) for a in all_activities]

    available_sessions = []
    activities = Activity.query.all()
    activities_dict = [activity.activity_to_dict() for activity in activities]

    if form.validate_on_submit():
        facility_id = int(form.facility_name.data)
        venue = Facility.query.get(facility_id)
        activity_id = Activity.query.filter_by(id = form.activity_name.data).first()
        venue_activity = Activity.query.filter_by(Activity_Name=activity_id.Activity_Name, facility_id=venue.id).first()
        if venue_activity:  # Check if venue_activity is not None
            group_size = form.size.data
            activity_price = venue_activity.Amount
            
            if venue:
                query = Sessions.query.filter(
                    Sessions.facility_id == venue.id,
                    Sessions.Date == form.date.data,
                    Sessions.activities.any(Activity.Activity_Name == activity_id.Activity_Name),
                    Sessions.Remaining_Cap >= form.size.data
                )

                if form.date.data == datetime.now().date():
                    current_time = datetime.now().time()
                    query = query.filter(Sessions.Start_time >= current_time)
                else:
                    query = query.filter(Sessions.Start_time >= venue.Start_Facility)
                
                print(f"Query: {query}")  # Debug print
                query_result = query.all()
                print(f"Query result: {query_result}")  # Debug print

                available_sessions = [{'session': session, 'activity_name': activity_id.Activity_Name} for session in query.all()]
                print(available_sessions)
                session_ids = [session['session'].id for session in available_sessions]
                session['available_session_ids'] = session_ids
                session['selected_activity_name'] = activity_id.Activity_Name
                return redirect(url_for('view_sessions', group_size=group_size, activity_price=activity_price))
            else:
                print("No activity found with the given name and facility")
    else:
        print("Form errors:", form.errors)

    return render_template('search_results.html', title='Search Venue', form=form, sessions=available_sessions, activities=activities_dict)

#page that displays all sessions that the user can book
#takes all the data previously filled by the user such as activity, facility ,date and group size to display all sessions in a tabular form

@app.route('/view_sessions', methods=['POST', 'GET'])
@login_required
@require_role(role="User")
def view_sessions():
    available_sessions = session.get('available_session_ids', [])
    selected_activity_name = session.get('selected_activity_name', None)
    group_size = request.args.get('group_size')
    activity_price = request.args.get('activity_price')
    print(activity_price)
    sessions_with_data = []

    for s in Sessions.query.filter(Sessions.id.in_(available_sessions)).all():
        for activity in s.facility.activities:
            if activity.Activity_Name == selected_activity_name:
                sessions_with_data.append({'session': s, 'activity_name': activity.Activity_Name,'activity_id':activity.id})

    return render_template('sessions.html', sessions=sessions_with_data,group_size=group_size,activity_price=activity_price)


@app.route('/book_session', methods=['POST'])
@login_required
# @require_role(role="User")
def book_session():
    session_id = request.form.get('session_id')
    activity_id = request.form.get('activity_id')
    user_id = current_user.id
    group_size = int(request.args.get('group_size'))
    activity_price = int(request.args.get('activity_price'))
    booking_Price = int(group_size * activity_price)
    # Get the session object
    session = Sessions.query.get(session_id)

    # Check if there's enough remaining capacity for the booking
    if session.Remaining_Cap >= group_size:
        booking = Booking(
            user_id=user_id,
            session_id=session_id,
            activity_id=activity_id,
            Book_Time = session.Date,
            Status="Saved",  
            Size=group_size,
            Amount = booking_Price
        )

        # Reduce the session's remaining capacity by the group size
        session.Remaining_Cap -= group_size

        db.session.add(booking)
        db.session.commit()

        # Add a message to notify the user that the booking was successful.
        flash('Booking successful!')
    else:
        flash('Not enough remaining capacity for the booking.')

    return redirect(url_for('checkout_page'))

#route that displays booking info in the cart
#Cart can be modified dynamically using ajax
#Discount amount of 15% is also passed in if the number of bookings is more that 3
@app.route('/checkout_page', methods=['POST', 'GET'])
@login_required
@require_role(role="User")
def checkout_page():
    data = Booking.query.filter_by(user_id=current_user.id,Status="Saved").all()
    total_amount = sum([item.Size * item.activity.Amount for item in data])
    grouped_data = defaultdict(list)
    
    for item in data:
        grouped_data[item.session_id].append(item)

    aggregated_data = []
    for session_id, items in grouped_data.items():
        total_size = sum(item.Size for item in items)
        aggregated_data.append({
            'item': items[0],
            'quantity': len(items),
            'total_size': total_size
        })
    discount = 0
    if len(aggregated_data) >= 3:
        discount = int(total_amount * 0.15)
    if current_user.Member == True:
        total_amount = 0
    

    return render_template('checkout_page.html', data=aggregated_data, total_amount=total_amount, discount=discount)

#Removes all expired bookings
@app.route('/delete_expired_booking', methods=['GET','POST'])
@login_required
@require_role(role="User")
def delete_expired_booking():
    print("Deleting expired bookings on the server...")
    user_bookings = Booking.query.filter_by(user_id=current_user.id, Status="Saved").all()

    for booking in user_bookings:
        session = Sessions.query.get(booking.session_id)
        session.Remaining_Cap += booking.Size
        db.session.delete(booking)

    db.session.commit()
    print("Deleted!")
    return {'status': 'success'}

#Route that deletes user booking
#Requires booking id
#Does not allow users to cancel bookings thaat were not made by them, Returning a 403 status code if the user tries to do so
#Else the booking is cancelled, The session remaining capacity is updated accordingly and success message is displayed
@app.route('/delete_booking/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@require_role(role="User")
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        abort(403)

    session_id = booking.session_id
    bookings_to_delete = Booking.query.filter_by(session_id=session_id, user_id=current_user.id).all()

    total_size = 0
    for b in bookings_to_delete:
        total_size += b.Size
        db.session.delete(b)

    session = Sessions.query.get(session_id)
    session.Remaining_Cap += total_size
    db.session.commit()

    flash('Booking has been deleted!', 'success')
    return redirect(url_for('checkout_page'))

#increase the booking size
#only bookings made by the user can be amended, else the 403 status code is returned
#If the booking was made by the user, Booking size increases and session capacity decreases
#If there are no more spaces left in the facility an appropriate error message is returned
#response is sent as JSON
@app.route('/increase_quantity/<int:booking_id>', methods=['POST'])
@login_required
@require_role(role="User")
def increase_quantity(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        abort(403)

    session = Sessions.query.get(booking.session_id)
    if session.Remaining_Cap > 0:
        booking.Size += 1
        booking.Amount = booking.Size * booking.activity.Amount
        session.Remaining_Cap -= 1
        db.session.commit()

        response = {
            'total_size': booking.Size,
            'amount': booking.Size * booking.activity.Amount,
            'status': 'success'
        }
    else:
        response = {
            'status': 'error',
            'message': 'No more available spots'
        }

    return jsonify(response)

#decrease the booking size
#only bookings made by the user can be amended, else the 403 status code is returned
#If the booking was made by the user, Booking size decreases and session capacity increases
#If there are no more spaces left in the facility an appropriate error message is returned
#response is sent as JSON
@app.route('/decrease_quantity/<int:booking_id>', methods=[ 'POST'])
@login_required
@require_role(role="User")
def decrease_quantity(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        abort(403)

    if booking.Size > 1:
        session = Sessions.query.get(booking.session_id)
        booking.Size -= 1
        booking.Amount = booking.Size * booking.activity.Amount
        session.Remaining_Cap += 1
        db.session.commit()

        response = {
            'total_size': booking.Size,
            'amount': booking.Size * booking.activity.Amount,
            'status': 'success'
        }
    else:
        response = {
            'status': 'error',
            'message': 'No more available spots'
        }

    return jsonify(response)

#route to see all user bookings That are Booked
@app.route('/my_bookings')
@login_required
@require_role(role="User")
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id, Status = "Booked").all()
    current_time = datetime.now().date()
    return render_template('my_bookings.html', bookings=bookings, current_time = current_time)

#Route that cancels the user booking
#Does not allow users to cancel bookings not made by them , returning status code 403 if the user tries to
#IF the booking was made by the user, the booking is cancelled and the remaining capacity of the session is updated
@app.route('/cancel_booking/<int:booking_id>')
@login_required
@require_role(role="User")
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        abort(403)
    session = Sessions.query.get(booking.session_id)
    session.Remaining_Cap += booking.Size
    booking.Status = "Cancelled"
    db.session.commit()
    flash("Booking has been cancelled successfully", "success")
    return redirect(url_for('my_bookings'))


@app.route('/get_activities/<int:facility_id>')
def get_activities(facility_id):
    facility = Facility.query.get(facility_id)
    activities = Activity.query.filter_by(facility_id=facility_id).all()
    activities_dict = [activity.activity_to_dict() for activity in activities]
    return jsonify(activities_dict)

@app.route('/get_activity_id/<activity_name>')
def get_activity_id(activity_name):
    activity = Activity.query.filter_by(Activity_Name=activity_name).first()
    if activity:
        return jsonify(activity.id)
    else:
        return jsonify(None)

@app.route('/facilities')
def facilities():
    facilities = Facility.query.all()
    return render_template('upcoming_sessions.html', facilities=facilities)

@app.route('/facility/<int:facility_id>/activity/<int:activity_id>/sessions')
def get_sessions_for_activity(facility_id, activity_id):
    sessions = Sessions.query.filter_by(facility_id=facility_id).join(session_activity_association).filter_by(activity_id=activity_id).all()
    session_dicts = [session.to_dict() for session in sessions]
    return jsonify(session_dicts)

#*********************************** End of User: After Login *****************************************
#rote to display the interactive calendar.
#Uses the calendar.js javascript library
#gets all activites for up to two weeks and converts this data into JSON
#Displays all activites from the current data up to two weeks
#Color codes the Data absed on Facility Name
#Also sepearate color is given to the user bookings.
@app.route('/calendar')
@require_role(role="User")
def calendar1():
    sessions = Sessions.query.all()
    user_bookings = Booking.query.filter_by(user_id=current_user.id, Status = "Booked").all()

    def get_event_color(Activity_name):
        if Activity_name == 'Swimming Pool':
            return 'orange'
        elif Activity_name == 'Fitness Room':
            return 'light orange'
        elif Activity_name == 'Squash Court 1':
            return 'dark yellow'
        elif Activity_name == 'Squash Court 2':
            return 'dark yellow'
        elif Activity_name == 'Sports Hall':
            return 'orange'
        elif Activity_name == 'Climbing Wall':
            return '#DEC20B'
        elif Activity_name == 'Studio':
            return '#B58B00'
        else:
            return 'black'

    events = []
    unique_activities = set()
    booked_events = []
    today = datetime.today().date()

     # Add booked sessions to the list
    for booking in user_bookings:
            session = booking.session
            activity = booking.activity
            event_color = get_event_color(session.facility.Name)
            if session.Date >= today:
                booked_events.append({'todo':  activity.Activity_Name, 'date': session.Date.isoformat(), 'color': 'green', 'Facility_name': session.facility.Name,'javadate':session.Date,'activityid':activity.id,'booked':True})

    # Add booked sessions to the list
    for booking in user_bookings:
        session = booking.session
        activity = booking.activity
        event_color = get_event_color(session.facility.Name)
        
        if session.Date >= today:
            events.append({'todo':  activity.Activity_Name, 'date': session.Date.isoformat(), 'color': 'green', 'Facility_name': session.facility.Name,'javadate':session.Date,'activityid':activity.id, 'booked': True})


    # Add available sessions to the list
    for session in sessions:
        if session.Date >= today:
            for activity in session.activities:
                unique_key = (activity.id, session.Date)
                if unique_key not in unique_activities:
                    event_color = get_event_color(session.facility.Name)  # get color based on activity name


                    events.append({'todo': activity.Activity_Name, 'date': session.Date.isoformat(), 'color': event_color, 'Facility_name': session.facility.Name,'javadate':session.Date,'activityid':activity.id, 'booked' : False})

                    unique_activities.add(unique_key)
     

    return render_template('calendar.html', events=events, booked_events=booked_events)

#Route that takes the session id , activity id and group size to make booking using the calendar
#Identifies the session and checks if the remaing cap is greater that party size
#Only valid party sizes can be used to save bookings.
@app.route('/calendar_book_session/<session_id>/<activity_id>/<int:group_size>', methods=['POST'])
@login_required
def calendarbook_session(session_id,activity_id,group_size):
    activity = Activity.query.filter_by(id = int(activity_id)).first()
    user_id = current_user.id
    booking_Price = int(group_size * activity.Amount)
    # Get the session object
    session = Sessions.query.get(int(session_id))

    # Check if there's enough remaining capacity for the booking
    if session.Remaining_Cap >= group_size:
        booking = Booking(
            user_id=user_id,
            session_id=int(session_id),
            activity_id=int(activity_id),
            Book_Time = session.Date,
            Status="Saved",  
            Size=group_size,
            Amount = booking_Price
        )
        # Reduce the session's remaining capacity by the group size
        session.Remaining_Cap -= group_size

        db.session.add(booking)
        db.session.commit()

        # Add a message to notify the user that the booking was successful.
        flash('Booking successful!')
    else:
        flash('Not enough remaining capacity for the booking.')

    return redirect(url_for('checkout_page'))

#route to retirve all available sessions given activity id, facility name , date
#This data is converted to JSON
#The JSON data is used to display the popup in the interactive calendar.
@app.route('/data_session/<activityid>/<facilityname>/<date>', methods=["POST"])
# @require_role(role="User")
@login_required
def calendar_session_on_hover(activityid, facilityname, date):
    facility = Facility.query.filter_by(Name=facilityname).first()
    activity = Activity.query.filter_by(id =activityid).first()
    data = []
    current_time = datetime.now().time()
    today = datetime.now().date()
    sessions = Sessions.query.filter_by(facility_id=facility.id, Date = date).all()
    for session in sessions:
        if activity in session.activities:
            if session.Date == today:
                if session.Start_time > current_time:
                    data.append({'session_id': session.id, 'Date': str(session.Date), 'Start_time': str(session.Start_time), 'End_time': str(session.End_time), 'Remaining_Cap': session.Remaining_Cap})
                    print(data)
            else:
                data.append({'session_id': session.id, 'Date': str(session.Date), 'Start_time': str(session.Start_time), 'End_time': str(session.End_time), 'Remaining_Cap': session.Remaining_Cap})
    return jsonify(data)

  
  ################################################analytics
#Loads the analytics page and the selectors required for retrieving relevant datta
@app.route('/analytics', methods=["GET", "POST"])
@require_role(role="Manager")
@login_required
def analytics():
    activityset = Activity.query.all()
    facilityset = Facility.query.all()
    current_year = datetime.utcnow().year
    current_year = datetime.utcnow().year
    start_of_year = datetime(current_year, 1, 1)
    end_of_year = datetime(current_year, 12, 31)
    next_year_start = datetime(current_year + 1, 1, 1)

    last_week_of_year = end_of_year - timedelta(days=end_of_year.weekday())
    next_year_first_week = next_year_start - timedelta(days=next_year_start.weekday())

    weeks_in_current_year = last_week_of_year.isocalendar()[1] + 1 if next_year_first_week.year != current_year else last_week_of_year.isocalendar()[1]

    week_data = []

    for week_number in range(1, weeks_in_current_year + 1):
        start_date = datetime.strptime(f"{current_year}-W{week_number-1}-1", "%Y-W%W-%w")
        end_date = start_date + timedelta(days=6)
        week_data.append((week_number, start_date.date(), end_date.date()))
    return render_template('analytics.html', title="Analytics",data =activityset,data1 = facilityset,week = week_data)


#Getter that retrieves the count of members and non members
#Sends this data in JSON form
#This data is passed on to google charts and displayed in the analytics page as a pie chart
@app.route('/analyzemember', methods=["GET","POST"])
@require_role(role="Manager")
@login_required
def analyze_members():
    total_users = UserAccount.query.count()
    member_users = UserAccount.query.filter_by(Member=True).count()
    non_member_users = UserAccount.query.filter_by(Member=False).count()
    data = {
        'members': member_users,
        'nonmembers': non_member_users,
    }
    return jsonify(data)


#Getter that calculated the average booking size.
#Take the total number of bookings, total size, average size and converts this data to JSON
#This data is displayed as a Table in the analytics page
@app.route('/analyzebookings', methods=["GET","POST"])
@require_role(role="Manager")
@login_required
def bookingstats():
    total_bookings = Booking.query.count()
    total_size = Booking.query.with_entities(db.func.sum(Booking.Size)).scalar()
    if total_size is None:
        total_size = 0
    if total_bookings > 0:
        avg_booking_size = int(total_size / total_bookings)
    else:
        avg_booking_size = 0
    data = {
        'totalbookings': total_bookings,
        'totalsize': total_size,
        'avgsize': avg_booking_size
    }
    return jsonify(data)

#Getter that ranks facilites according to utilization or Number of bookings depending on user choice
#Converts the data to JSON which is then converted to Tabular data for the analytics page
#Takes the ranking, Facility name and filter type and converts this data
@app.route('/rankfacilities/<filter_type>', methods=["GET","POST"])
@require_role(role="Manager")
@login_required
def rankfacilities(filter_type):
    if filter_type == "Booking":
        popular_facilities = db.session.query(Facility.Name, db.func.count(Booking.id).label('bookings')).\
                            outerjoin(Sessions, Sessions.facility_id == Facility.id).\
                            outerjoin(Booking, Booking.session_id == Sessions.id).\
                            group_by(Facility.id).\
                            order_by(db.func.count(Booking.id).desc()).all()
        facility_ranking = []
        for i, (facility, booking_count) in enumerate(popular_facilities):
            facility_ranking.append({
                'ranking': i + 1,
                'facility_name': facility,
                'booking_count': booking_count
            })
        return jsonify(facility_ranking)

    elif filter_type == "Utilization":
        utilization_query = db.session.query(Facility.Name,func.avg(Booking.Size * 1.0 / Facility.Capacity) * 100).\
        outerjoin(Sessions).\
        outerjoin(Booking).\
        group_by(Facility.id).\
        all()    
        utilization = []
        i = 1
        for facility_name, avg_utilization in utilization_query:
            if avg_utilization is None:
                avg_utilization = 0
            utilization.append({
                'ranking': i,
                "facility_name": facility_name,
                "booking_count": int(avg_utilization)
            })
            i+=1
        return jsonify(utilization)
    else:
        return jsonify(error="Invalid filter type"), 400

#getter to get the monthly reveneue by facility for a given month and year selected by the user
#Converts this data to JSON which is used by Google Charts to create a bar chart
@app.route('/getrevenues/<monthsel>/<yearsel>', methods=["GET","POST"])
@require_role(role="Manager")
@login_required
def get_revenues(monthsel,yearsel):
    monthly_revenue = db.session.query(
            Facility.Name,
            extract('year', Booking.Book_Time).label('year'),
            extract('month', Booking.Book_Time).label('month'),
            func.sum(Booking.Amount).label('total_revenue')
        ).join(Sessions, Facility.id == Sessions.facility_id).join(
            Booking, Sessions.id == Booking.session_id
        ).group_by(
            Facility.id, extract('year', Booking.Book_Time), extract('month', Booking.Book_Time)
        ).order_by(
            Facility.Name, extract('year', Booking.Book_Time), extract('month', Booking.Book_Time)
        ).all()

    monthly_revenue_dict = {}
    for facility_name, year, month, total_revenue in monthly_revenue:
        if year == int(yearsel) and month == int(monthsel):
            if facility_name not in monthly_revenue_dict:
                monthly_revenue_dict[facility_name] = []
            monthly_revenue_dict[facility_name].append({
                'year': year,
                'month': month,
                'total_revenue': total_revenue
            })

    return jsonify(monthly_revenue_dict)

#************************************ Update User Information ********************************************
#Route that allows the user to update their personal information
#Displays the existing information
@app.route('/update_user', methods=['GET', 'POST'])
@login_required
def update_user():
    form = UpdateUserForm()
    if form.validate_on_submit():
        current_user.User = form.User.data
        current_user.set_password(form.password.data)
        current_user.Email = form.email.data
        current_user.Mobile = form.mobile.data
        db.session.commit()
        flash('Your personal information has been updated!', 'success')
        return redirect(url_for('user'))
    elif request.method == 'GET':
        form.User.data = current_user.User
        form.email.data = current_user.Email
        form.mobile.data = current_user.Mobile
    return render_template('update_user.html', title='Update Personal Information', form=form)

#Route to display user information
@app.route('/user_information')
@login_required
def user_information():
    return render_template('user_information.html', title='User Account')


#************************************ End of User Information ********************************************

#getter that is used to retrieve weekly data of Facility
#Weekly data can be percentage utilization or reveneues by all Facilityies
#Returns the data depending on the user choice to the analytics page as JSON which is used by google charts to create a bar chart.
@app.route('/facilitywiseinfo/<string:usagetype>/<int:week>', methods=["GET", "POST"])
@require_role(role="Manager")
@login_required
def facilitywiseinfo(usagetype, week):
    current_year = datetime.utcnow().year

    facilities = Facility.query.all()

    facility_data = []
    week = week - 1


    if usagetype == "Utilization":
        for facility in facilities:
            bookings = Booking.query.join(Sessions).filter(
                Sessions.facility_id == facility.id,
                extract('year', Sessions.Date) == current_year,
                extract('week', Sessions.Date) == week
            ).all()


            capacity = facility.Capacity
            total_booked = sum(booking.Size for booking in bookings)
            utilization = total_booked / capacity * 100 if capacity > 0 else 0

            facility_data.append({'facility_name': facility.Name, 'data': utilization})

    elif usagetype == "Revenue":
        weekly_revenue = db.session.query(
            Facility.Name,
            func.sum(Booking.Amount).label('revenue')
        ).join(Sessions, Facility.id == Sessions.facility_id).join(
            Booking, Sessions.id == Booking.session_id
        ).filter(
            extract('year', Sessions.Date) == current_year,
            extract('week', Sessions.Date) == week
        ).group_by(
            Facility.Name
        ).order_by(
            Facility.Name
        ).all()

        print(f"Weekly revenue: {weekly_revenue}")

        for facility_revenue in weekly_revenue:
            facility_data.append({'facility_name': facility_revenue[0], 'data': facility_revenue[1]})

    return jsonify(facility_data)

#getter that is used to retrieve weekly data of activites
#Weekly data can be number of bookings or reveneues by all activites
#Returns the data depending on the user choice to the analytics page as JSON which is used by google charts to create a bar chart.
@app.route('/activitywiseinfo/<string:usagetype>/<int:week>', methods=["GET", "POST"])
@require_role(role="Manager")
@login_required
def activitywiseinfo(usagetype, week):
    current_year = datetime.utcnow().year

    activities = Activity.query.all()

    activity_data = []
    week = week - 1


    if usagetype == "Bookings":
        for activity in activities:
            bookings_count = Booking.query.join(Sessions).filter(
                Booking.activity_id == activity.id,
                extract('year', Sessions.Date) == current_year,
                extract('week', Sessions.Date) == week
            ).count()


            activity_data.append({'activity_name': activity.Activity_Name + ' : ' + activity.facility.Name, 'data': bookings_count})

    elif usagetype == "Revenue":
        weekly_revenue = db.session.query(
            Activity.Activity_Name,
            Facility.Name,
            func.sum(Booking.Amount).label('revenue')
        ).select_from(Booking).join(
            Sessions, Sessions.id == Booking.session_id
        ).join(
            Activity, Booking.activity_id == Activity.id
        ).join(
            Facility, Activity.facility_id == Facility.id
        ).filter(
            extract('year', Sessions.Date) == current_year,
            extract('week', Sessions.Date) == week
        ).group_by(
            Activity.Activity_Name,
            Facility.Name
        ).order_by(
            Activity.Activity_Name,
            Facility.Name
        ).all()

        print(f"Weekly revenue: {weekly_revenue}")

        for activity_revenue in weekly_revenue:
            activity_data.append({'activity_name': activity_revenue[0] + ' : ' + activity_revenue[1] , 'data': activity_revenue[2]})

    return jsonify(activity_data)

#Route that handles the contact requests
#Sends the acknowledgement to the user via email if the data entered is valid.
@app.route('/contact_us', methods=['GET', 'POST'])
def contact_us():
  form = ContactUsForm()
  if request.method == 'POST':
    if form.validate() == False:
      flash('All fields are required.')
      return render_template('contact_us.html', form=form)
    else:
        subject = 'Message Recieved'

        body = render_template('contact_us_email.html', user_email = form.email.data)
        message = Message(subject, recipients=[form.email.data], html=body,sender = 'arjun.krishnan0033@gmail.com')

        mail.send(message)
        return redirect('/')
  elif request.method == 'GET':
    return render_template('contact_us.html', form=form)

#Route that handles the refund requests
#Sends the acknowledgement to the user via email if the data entered is valid.
@app.route('/refund_form',methods=["GET", "POST"])
def refund():
    form = RefundForm()
    if request.method == 'POST':
        if form.validate() == False:
            flash('All fields are required.')
            return render_template('refund.html', form=form)
        else:
            subject = 'Refund request processed'

            body = "Your booking refund request has now been processed!"
            message = Message(subject, recipients=[form.email.data], html=body,sender = 'arjun.krishnan0033@gmail.com')

            mail.send(message)
        return redirect('/')

    return render_template('refund.html', title='refund', form=form)


#getter that gets all faciltiy ids and Facility names and Converts data to JSOM
@app.route('/get_facilities', methods=["GET", "POST"])
@login_required
def get_all_facilities():
    facilities = Facility.query.all()
    data = []
    for fac in facilities:
        data.append({'id':fac.id,'Name':fac.Name})
    return jsonify(data)
