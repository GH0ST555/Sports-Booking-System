from app import db
from app.models import Sessions,Facility,Activity


#Script to delete all facilites, activites and sessions
def delete_sessions():
    Facility.query.delete()
    Activity.query.delete()
    Sessions.query.delete()
    db.session.commit()

if __name__ == '__main__':
    delete_sessions()
