from datetime import datetime, timedelta, time
from app import db
from app.models import  Sessions, Activity, Facility

def generate_sessions():
    # Get the current date and time
    now = datetime.utcnow()

    # Calculate the date two weeks from now
    two_weeks_from_now = now + timedelta(days=14)

    # Query the database for all activities and facilities
    activities = Activity.query.all()
    facilities = Facility.query.all()

    # Generate new sessions for exactly two weeks from today
    start_time = time(hour=9, minute=0, second=0)
    end_time = time(hour=21, minute=0, second=0)

    for date in (now.date() + timedelta(n) for n in range(14)):
        # Check if a session already exists for this date
        existing_session = Sessions.query.filter_by(Date=date).first()

        if existing_session:
            # If a session already exists, skip this date
            continue
        else:
            # If a session doesn't exist, create a new session for each facility
            for facility in facilities:
                start_facility_time = datetime.strptime(facility.Start_Facility, '%H:%M').time()
                end_facility_time = datetime.strptime(facility.End_Facility, '%H:%M').time()
                current_time = datetime.combine(date, start_time)
                end_datetime = datetime.combine(date, end_time)
                activities_for_facility = [activity for activity in activities if activity.facility_id == facility.id]

                while current_time < end_datetime:
                    new_session = Sessions(Date=date,
                                           Start_time=current_time.time(),
                                           End_time=(current_time + timedelta(hours=1)).time(),
                                           Remaining_Cap=facility.Capacity,
                                           facility_id=facility.id)

                    for activity in activities_for_facility:
                        new_session.activities.append(activity)

                    db.session.add(new_session)

                    current_time += timedelta(hours=1)

    # Commit the changes to the database
    db.session.commit()



if __name__ == '__main__':
    generate_sessions()
