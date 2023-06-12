##  Testing Framework And Configuration
* Testing was done using the pytest and pytest-flask modules
* Conftest.py creates an application in test context which uses an in-memory Database which prevents actual data being compromised.
* Conftest.py also initializes this database with some sample activities, sessions, facilities and users of each type to conduct thorough testing.

## Test Breakdown
### Methods
* login_user: logs in the user. Used for tests that require the user account authenticated. Returns the logged in instance for testing.
* login_employee: logis in the employee/manager. Used for tests that require the employee/manager account authenticated. Returns the logged in instance  for testing.

### Tests
* test_post_for_user(test_app, test_database): Tests the create user account function. Checks the database to ensure that the user account is present in the database and the correct response code is created.<br>
Expected output: True , 200<br>
Actual output: True, 200<br>
<br>

* test_user(test_app, test_database): Tests if the sample user created in the test database exists and tests if the values are matching.<br>
Expected output: True , True, True, True, True<br>
Actual output: True, True, True, True, True<br>
<br>

* test_emp(test_app, test_database): Tests if the sample employee created in the test database exists and tests if the values are matching.<br>
Expected output: True , True, True, True, True<br>
Actual output: True, True, True, True, True<br>
<br>

* test_mgr(test_app, test_database): Tests if the sample manager created in the test database exists and tests if the values are matching.<br>
Expected output: True , True, True, True, True<br>
Actual output: True, True, True, True, True<br>
<br>

* test_standard_routes(test_app): Tests all routes that do not require user authentication. Expects return code 200 indicating that the pages are accessible.<br>
Expected output: True , True, True, True, True, True<br>
Actual output: True, True, True, True, True, True<br>
<br>


* test_login_manager_protected_routes(test_app): Tests all routes that do require Manager account authentication. Expects return code 200 indicating that the pages are accessible.<br>
Expected output: True , True, True, True<br>
Actual output: True, True, True, True<br>
<br>

* test_create_employee_accounts(test_app,test_database): Logs in to the sample manager account to test if an employee account can be created. Checks the database to confirm the details are present and ensures status code is correct (200) for the POST request.<br>
Expected output: True , 200<br>
Actual output: True, 200<br>
<br>

* test_create_manager_accounts(test_app,test_database): Logs in to the sample manager account to test if a manager account can be created. Checks the database to confirm the details are present and ensures status code is correct (200) for the POST request.<br>
Expected output: True , 200<br>
Actual output: True, 200<br>
<br>

* test_create_facility(test_app,test_database): Logs in to the sample manager account to test if a facility can be created. Checks the database to confirm the details are present and ensures status code is correct (200) for the POST request.<br>
Expected output: True , 200<br>
Actual output: True, 200<br>
<br>

* test_update_user(test_app, test_database): Logs in to the sample user account to test if user account information can be updated. Checks the database to confirm the details are present and ensures status code is correct (200) for the POST request.<br>
Expected output: True , True<br>
Actual output: True, True<br>
<br>

* def test_2fa_post_request(test_app, test_database): Tests the Two-Factor authentication by sending a sample request. Checks if the POST request is successful (302)<br>
Expected output: 302<br>
Actual output: 302<br>
<br>

* test_invalid_number_2FA_request(test_app, test_database): Tests the Two-Factor authentication error handling when inputting an invalid mobile number.Checks if the POST request is successful (302)<br>
Expected output: 302<br>
Actual output: 302<br>
<br>

* test_forget_password(test_app, test_database): Tests the reset password functionality. Logs the user in and sends a POST request and the test checks in the database to assert weather the password has changed.<br>
Expected output: 302<br>
Actual output: 302<br>
<br>

* test_forget_password_invalid_info(test_app, test_database): Tests the reset password functionality. Logs the user in and sends a POST request giving an invalid user and the test checks in the database to assert weather the password has changed. Returns 200 as the page will reload.<br>
Expected output: 200<br>
Actual output: 200<br>
<br>

* test_preset_booking(test_app, test_database): Checks if the booking created in the config exists in the database.<br>
Expected output: True, True<br>
Actual output: True, True<br>
<br>

* test_successful_booking(test_app, test_database): Tests gets the payment_success route which is used to check if the users booking status has changed.
Expected output: 200<br>
Actual output: 200<br>
<br>

* test_get_facility_data(test_app): Logs in using manager credentials and tests the facility information getter is working.<br>
    Expected output:200 <br>
    Expected json:{
        'name': 'Test Facility',
        'capacity': 100,
        'start_time': '00:00:00',
        'end_time': '23:59:59'
    }<br>
    Actual output:200 <br>
    Actual json:{
        'name': 'Test Facility',
        'capacity': 100,
        'start_time': '00:00:00',
        'end_time': '23:59:59'
    }<br><br>
* test_invalid_get_facility_data(test_app): Logs in using manager credentials and tests the facility information getter is working when invalid facility is requested.<br>
    Expected output:200 <br>
    Expected json:{
        'error': 'Facility not found'
    }<br>
    Actual output:200 <br>
    Actual json:{
        'error': 'Facility not found'
    }<br><br>

* test_get_activity_data(test_app): Logs in using manager credentials and tests the activity information getter is working for a valid activity.<br>
    Expected output:200 <br>
    Expected json: {
        'name': 'Test Activity',
        'amount': 10,
        'facility_id': 1,
    }<br>
    Actual output:200 <br>
    Actual json: {
        'name': 'Test Activity',
        'amount': 10,
        'facility_id': 1,
    }<br><br>
* test_get_invalid_activity_data(test_app): Logs in using manager credentials and tests the error handling of an invalid activity id.<br>
    Expected output:200 <br>
    Expected json:{
        'error': 'Activity not found'
    }<br>
    Actual output:200 <br>
    Actual json: {
        'error': 'Activity not found'
    }<br><br>

* test_get_activity_linked_to_facility(test_app): Tests the Activity-Facility getter.<br>
    Expected output:200 <br>
    Expected json: [{'Activity_Name': 'Test Activity', 'Amount': 10, 'facility_id': 1, 'id': 1}]<br>
    Actual output:200 <br>
    Actual json: [{'Activity_Name': 'Test Activity', 'Amount': 10, 'facility_id': 1, 'id': 1}]<br><br>

* test_delete_booking(test_app, test_database): Tests weather the delete booking function is working correctly. <br>
Expected output:200 <br>
Actual output:200 <br>

* test_create_activity(test_app,test_database): Logs in using manager credentials to test the create activity function is working.<br>
Expected output:200, True <br>
Actual output:200, True <br>

* test_user_membership_cancellation(test_app, test_database): Logs in using employee credentials to test the ability of employees to amend user memberships.<br>
Expected output:True,200, True <br>
Actual output:True,200, True <br>

* test_user_yearly_membership(test_app, test_database): Tests the ability of users to sign up for yearly memberships. <br>
Expected output: True, True, True, True <br>
Actual output: True, True, True, True <br>

* test_user_monthly_membership(test_app, test_database): Tests the ability of users to sign up for monthly memberships. <br>
Expected output: True, True, True, True <br>
Actual output: True, True, True, True <br>

* test_booking_success(test_app, test_database):  Tests the ability of users to add bookings to checkout. <br>
Expected output: 302, True <br>
Actual output: 302, True <br>

* test_update_facility(test_app, test_database): Logs in using manager credentials to test the ability to update facility details.<br>
Expected output: True, True, True, True <br>
Actual output: True, True, True, True <br>

* test_update_activity(test_app, test_database): Logs in using manager credentials to test the ability to update activity details.<br>
Expected output: True, True<br>
Actual output: True, True <br>

* test_book_session_emp(test_app, test_database): Logs in using employee credentials to test the ability for employees to make bookings on behalf of the user.<br>
Expected output: True, True, True, True, True, True, True, True <br>
Actual output: True, True, True, True, True, True, True, True <br>
