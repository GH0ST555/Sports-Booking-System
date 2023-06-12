from app import app,db
from app.models import Facility, Activity, Sessions
from datetime import date,time,timedelta,datetime



#Script that creates sample sessions for a limited number of days instead of 2 weeks
#Useful for testing on systems that are slower.
#Recommended for SOC machines

# Facilities
facilities = [
    {"Name": "Swimming Pool", "Capacity": 30, "Start_Facility": "08:00", "End_Facility": "20:00"},
    {"Name": "Fitness Room", "Capacity": 35, "Start_Facility": "08:00", "End_Facility": "22:00"},
    {"Name": "Squash Court", "Capacity": 4, "Start_Facility": "08:00", "End_Facility": "22:00"},
    {"Name": "Sports Hall", "Capacity": 45, "Start_Facility": "08:00", "End_Facility": "22:00"},
    {"Name": "Climbing Wall", "Capacity": 22, "Start_Facility": "10:00", "End_Facility": "20:00"},
    {"Name": "Studio", "Capacity": 25, "Start_Facility": "08:00", "End_Facility": "22:00"},
]


# Activities
activities_data = [
    {"facility_name": "Swimming Pool", "Activity_Name": "General use", "Amount": 10},
    {"facility_name": "Swimming Pool", "Activity_Name": "Lane swimming", "Amount": 20},
    {"facility_name": "Swimming Pool", "Activity_Name": "Lessons", "Amount": 30},
    {"facility_name": "Swimming Pool", "Activity_Name": "Team events", "Amount": 22},
    {"facility_name": "Fitness Room", "Activity_Name": "General use", "Amount": 20},
    {"facility_name": "Squash Court", "Activity_Name": "1-hour sessions", "Amount": 50},
    {"facility_name": "Sports Hall", "Activity_Name": "1-hour sessions", "Amount": 35},
    {"facility_name": "Sports Hall", "Activity_Name": "Team events", "Amount": 25},
    {"facility_name": "Climbing Wall", "Activity_Name": "General use", "Amount": 40},
    {"facility_name": "Studio", "Activity_Name": "Exercise classes", "Amount": 30},
]


# Create sessions
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# Helper function to generate hourly time slots between two times
def generate_time_slots(start_time, end_time):
    time_slots = []
    while start_time < end_time:
        time_slots.append(start_time.time())  # Convert datetime back to time
        start_time += timedelta(hours=1)
    return time_slots


def generate_sessions(facility, start_time, end_time):
    facility_obj = Facility.query.filter_by(Name=facility).first()
    if facility_obj:
        activities = Activity.query.filter_by(facility_id=facility_obj.id).all()
        today = datetime.today()
        for day_offset in range(2):  # Loop through the days in the 2-week period
            day_date = today + timedelta(days=day_offset)
            start_datetime = datetime.combine(day_date, start_time)
            end_datetime = datetime.combine(day_date, end_time)

            time_slots = generate_time_slots(start_datetime, end_datetime)
            for slot in time_slots:
                start_slot = slot
                end_slot = (datetime.combine(day_date, slot) + timedelta(hours=1)).time()
                session_obj = Sessions(Date=day_date, Start_time=start_slot, End_time=end_slot,
                                Remaining_Cap=facility_obj.Capacity, facility_id=facility_obj.id)
                for activity in activities:
                    session_obj.activities.append(activity)
                    db.session.add(session_obj)
                db.session.commit()


def main():
    # Populate the Facility table
    for facility in facilities:
        facility_obj = Facility(
            Name=facility["Name"],
            Capacity=facility["Capacity"],
            Start_Facility=facility["Start_Facility"],
            End_Facility=facility["End_Facility"],
        )
        db.session.add(facility_obj)
    db.session.commit()

   # Populate the Activity table
    for activity in activities_data:
        facility_obj = Facility.query.filter_by(Name=activity["facility_name"]).first()
        if facility_obj:
            existing_activity = Activity.query.filter_by(facility_id=facility_obj.id, Activity_Name=activity["Activity_Name"]).first()
            if not existing_activity:  # Check if the activity does not exist
                activity_obj = Activity(Activity_Name=activity["Activity_Name"], Amount=activity["Amount"])
                activity_obj.facility = facility_obj
                db.session.add(activity_obj)

    db.session.commit()


    # Generate sessions for each facility
    for facility in facilities:
        start_time = datetime.strptime(facility["Start_Facility"], "%H:%M").time()
        end_time = datetime.strptime(facility["End_Facility"], "%H:%M").time()
        generate_sessions(facility["Name"], start_time, end_time)

    db.session.commit()



if __name__ == '__main__':
    main()
