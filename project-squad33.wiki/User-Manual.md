## For Windows Machines:
All necessary files are inside the code directory. <br>
To create a virtual environment:<br>
code - 'python -m venv /path/to/new/virtual/environment'<br>
To activate your virtual environment: go to the directory where your environment is located and type - '.venv\Scripts\Activate'<br>
When your venv is activated, go to the directory with requirements.txt file in it (inside the code directory) and type- 'pip install -m requirements.txt'<br>
After all modules are installed:
* If app.db is present: just set the flask app- 'set FLASK_APP=run.py' and run the application using 'flask run'
* If app.db is not present: initialize the db- 'flask db init' , create migrations -'flask db migrate -m "message", 'flask db upgrade' and then run the script 'python add_roles.py' followed by the script 'python add_sessions.py'  after which follow the steps mentioned above as we now have app.db.

To Test the application:<br>
In the code directory type - pytest

## For Mac computers:
To activate your virtual environment: go to the home directory and enter the command- 'source flask/bin/activate' or 'conda activate venv_name"<br>
When your venv is activated, go to the directory with requirements.txt file in it (inside the code directory) and type- 'pip install -m requirements.txt'<br>
After all modules are installed:
* If app.db is present: Run the application using 'flask run'
* If app.db is not present: initialize the db- 'flask db init' , create migrations -'flask db migrate -m "message", 'flask db upgrade' and then run the script 'add_roles.py' followed by the script 'python add_sessions.py' after which follow the steps mentioned above as we now have app.db.

To Test the application:<br>
In the code directory enter the command- pytest

## For SOC Linux machines:
Follow the WEB APP module content.Only Section 1 content is required.<br>
To activate your virtual environment: go to the home directory and enter the command- 'source flask/bin/activate'<br>
When your venv is activated, go to the directory with requirements.txt file in it (inside the code directory) and type- 'pip install -m requirements.txt'<br>
After all modules are installed:
* If app.db is present: Run the application using 'flask run'
* If app.db is not present: initialize the db- 'flask db init' , create migrations -'flask db migrate -m "message", 'flask db upgrade' and then run the script 'add_roles.py' followed by the script 'python add_sessions.py' after which follow the steps mentioned above as we now have app.db.

To Test the application:<br>
In the code directory enter the command- pytest


### IF Your Python version is 3.7 and above
remove the dataclasses=0.8 module from requirements.txt as this is included in all versions from 3.7 and above. applicable to those who want to run this code on their personal machines.

