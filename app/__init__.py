from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from sqlalchemy import event, MetaData
from sqlalchemy.engine import Engine
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = '6c98006fc6f94fe0ec02f4955696182c'

# https://stackoverflow.com/questions/5890250/on-delete-cascade-in-sqlite3
# Foriegn key support is not by default on in SQLite. Any fk operations like
# on-delete cascade etc. won't work. You have to ON it in PRAGMA every time
# you connect to the database.
# WILL NOT WORK - app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db?foreign_keys=on'
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # SQLite-specific pragma to enforce foreign key constraints
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()

app.config['UPLOAD_FOLDER'] = r'static'
app.config['UPLOAD_PROFESSIONAL_ID'] = r'professional_ids'
app.config['UPLOAD_PROFESSIONAL_PROFILE'] = r'professional_profiles'
app.config['UPLOAD_PROFESSIONAL_RESUME'] = r'professional_resumes'
app.config['UPLOAD_SERVICE_PROFILE'] = r'services'

image_size = (200, 200)

# Naming constraints becomes important when migrating changes in 
# constraints to the database. Without names, flask-migrate would
# not be able to identify which constraints to update as there could
# be many constraints of the same type in a table. 
convention = {
  "ix": "ix_%(column_0_label)s",
  "uq": "uq_%(table_name)s_%(column_0_name)s",
  "ck": "ck_%(table_name)s_%(constraint_name)s",
  "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
  "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(app, metadata=metadata)

migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'danger'

# https://stackoverflow.com/questions/6036082/call-a-python-function-from-jinja2
# Adding utility functions to jinja templates
func_dict = {
    "current_time": datetime.now,
    "timedelta": timedelta,
    "list": list,
}
app.jinja_env.globals.update(func_dict)

# Adding a scheduler to expire service requests every 1 minutes
scheduler = BackgroundScheduler()

def expire_service_requests():
    now = datetime.now()
    with app.app_context():
        expired_requests = ServiceRequest.query.filter(
            ServiceRequest.expiry_date <= now,
            ServiceRequest.status_id == RequestStatus.query.filter_by(status="Pending").first().id
        ).all()

        for request in expired_requests:
            request.status_id = RequestStatus.query.filter_by(status="Expired").first().id
            db.session.commit()

        print(f"{len(expired_requests)} service requests expired.")

scheduler.add_job(
    func=expire_service_requests, 
    trigger=IntervalTrigger(minutes=1), 
    id='expire_service_requests', 
    name='Expire pending service requests every 1 minutes', 
    replace_existing=True
)

scheduler.start()
atexit.register(lambda: scheduler.shutdown())

from app.models import *
from app.routes import *

@app.errorhandler(403)
def page_not_found(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404



