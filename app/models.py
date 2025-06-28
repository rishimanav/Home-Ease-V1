"""
SQLAlchemy ORM model classes for the household services database (SQLite).
"""

from sqlalchemy import UniqueConstraint
from app import app, db, login_manager
from flask_login import UserMixin

"""
How to implement constraints on role?
https://stackoverflow.com/questions/5299267/how-to-create-enum-type-in-sqlite
Best option is to use Enums. But SQLite does not support it.
CheckConstraint can be used, BUT, there are some issues - 
 1. CheckConstraint can not fully emulate enums, beciause it makes it impossible to sort by
    the integer index of the values, which is possible by enums.
 2. The storage overhead should be taken as a caveat as well. While constraints can be used
    to ensure data integrity, and while an index may make queries fast, you are still storing
    strings (Storing strings ("Admin", "Customer") takes more space than storing small integers 
    (as Enums would))- if used extensively, this requires several times more storage than 
    proper enums, depending on string lengths. You might need to consider using additional 
    lookup tables and foreign keys to work around this issue.
 3. Problem with the check is that the values are 'magic strings'. You cannot reference them
    somewhere else, like pull them into your code base and use them. They can't be reused 
    across the system without repeating them manually, increasing the risk of errors or 
    inconsistencies.
Workaround Using Lookup Tables:
  A more efficient solution could involve using lookup tables where you define roles with 
  their associated integer IDs. For example: A roles table with columns id (integer) and 
  name (string). Use foreign keys in your main user table to reference roles by their ID. 
  This way, you can:
   1. Store integers (which are space-efficient).
   2. Avoid magic strings.
   3. Enable sorting by role IDs.
"""

"""
Since relationships are an ORM facility, they have nothing to do with database schema, 
and thus don't require you to migrate any changes in them. 
"""

"""
https://stackoverflow.com/questions/30406808/flask-sqlalchemy-difference-between-association-model-and-association-table-fo
db.Table is typically used for pure association tables where the table serves as a 
bridge between two models, without any additional fields apart from foreign keys. 
However, as soon as you want to include additional fields (like comments), it is
better to use a proper db.Model class.
""" 

@login_manager.user_loader
def load_user(user_id):
    """
    Method to load the logged in user as current_user.
    """
    return User.query.get(int(user_id))

zipcode_service = db.Table(
    'zipcode_service',
    db.Column('zipcode_id', db.Integer, db.ForeignKey('Zipcode.id', ondelete='CASCADE'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('Service.id', ondelete='CASCADE'), primary_key=True)
)

class User(db.Model, UserMixin):
    """
    Model to store the accounts on the app.
    Stores the account credentials
    """
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    account_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    last_login_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    reports = db.Column(db.Integer, nullable=False, default=0)

    # Foreign Keys
    role_id = db.Column(db.Integer, db.ForeignKey('UserRole.id'), nullable=False)

    # Relationships
    role = db.relationship('UserRole', back_populates='users', lazy=True)
    customer = db.relationship('Customer', back_populates='user', lazy=True)
    professional = db.relationship('Professional', back_populates='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}({self.role})>'

class Customer(db.Model):
    """
    Model to store a customer's profile.
    """
    __tablename__ = 'Customer'
    
    # Personal profile attributes
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(20), unique=True, nullable=False)
    last_name = db.Column(db.String(20), unique=True, nullable=False)
    dob = db.Column(db.DateTime, nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(200), nullable=False)

    # average_rating = db.Column(db.Float, nullable=False, default=0.0)
    # total_ratings = db.Column(db.Integer, nullable=False, default=0)
    # strikes = db.Column(db.Integer, nullable=False, default=0)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'), unique=True, nullable=False)
    zipcode_id = db.Column(db.Integer, db.ForeignKey('Zipcode.id'), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='customer', lazy=True)
    zipcode = db.relationship('Zipcode', back_populates='customers', lazy=True)
    service_requests = db.relationship('ServiceRequest', back_populates='customer', lazy=True)
    reviews_received = db.relationship('CustomerReview', back_populates='customer', lazy=True)
    professional_review = db.relationship('ProfessionalReview', back_populates='customer', lazy=True)

    def __repr__(self): 
        return f'<Customer {self.name}>'

class Professional(db.Model):
    """
    Model to store a professional's profile.
    """
    __tablename__ = 'Professional'
    
    # personal profile attributes
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(20), nullable=False)
    dob = db.Column(db.DateTime, nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(200), nullable=False)

    # professional profile attributes
    about = db.Column(db.String(500), nullable=True)
    experience = db.Column(db.Integer, nullable=False)
    profile_img = db.Column(db.String(255), nullable=False, default="professional_profiles/professional_default.jpg")
    id_proof = db.Column(db.String(255), nullable=False)
    resume = db.Column(db.String(255), nullable=False)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)

    # average_rating = db.Column(db.Float, nullable=False, default=0.0)
    # total_ratings = db.Column(db.Integer, nullable=False, default=0)
    # strikes = db.Column(db.Integer, nullable=False, default=0)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'), unique=True, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('Service.id', ondelete='SET NULL'), nullable=False)
    zipcode_id = db.Column(db.Integer, db.ForeignKey('Zipcode.id'), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='professional', lazy=True)
    zipcode = db.relationship('Zipcode', back_populates='professionals', lazy=True)
    scrutiny_requests = db.relationship("ScrutinyRequest", back_populates='professional', lazy=True)
    service = db.relationship("Service", back_populates='professionals', lazy=True)
    service_requests = db.relationship('ServiceRequest', back_populates='professional', lazy=True)
    ignore_logs = db.relationship('IgnoreLog', back_populates='professional', lazy=True)
    customer_review = db.relationship('CustomerReview', back_populates='professional', lazy=True)
    reviews_received = db.relationship('ProfessionalReview', back_populates='professional', lazy=True)

    def __repr__(self):
        return f'<Professional {self.first_name}>'

class ScrutinyRequest(db.Model):
    """
    Model to store admin actions while professional scrutiny.
    """
    __tablename__='ScrutinyRequest'
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, default=db.func.current_timestamp())
    comments = db.Column(db.Text)

    # Foreign Keys
    professional_id = db.Column(db.Integer, db.ForeignKey('Professional.id', ondelete='CASCADE'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('ScrutinyStatus.id'), nullable=False)

    # Relatonships
    professional = db.relationship("Professional", back_populates='scrutiny_requests', lazy=True)
    status = db.relationship("ScrutinyStatus", back_populates='scrutiny_requests', lazy=True)

class ScrutinyStatus(db.Model):
    """
    Model to store types of scrutiny results.
    Pending (1) - Scrutiny of application is pending.
    Verified (2) - Scrutiny found no problems with application.
    Rejected (3) - Scrutiny found problems with application.
    """
    __tablename__='ScrutinyStatus'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(), unique=True, nullable=False)

    # Relationships
    scrutiny_requests = db.relationship("ScrutinyRequest", back_populates='status', lazy=True)

class Category(db.Model):
    """
    Model to store the various categories of services offered.
    """
    __tablename__ = 'Category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    

    # Relationships
    services = db.relationship('Service', back_populates='category', lazy=True, passive_deletes=True)

class Service(db.Model):
    """
    Model to store the various services offered.
    """
    __tablename__ = 'Service'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    base_price = db.Column(db.Float, nullable=False)
    estimated_duration = db.Column(db.Integer, nullable=False)  # in hours
    image = db.Column(db.String(255), nullable=False, default="services/service_default.jpg")
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    # Foreign Keys
    category_id = db.Column(db.Integer, db.ForeignKey('Category.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    category = db.relationship('Category', back_populates='services', lazy=True)
    zipcodes = db.relationship('Zipcode', secondary=zipcode_service, back_populates='services', passive_deletes=True)
    professionals = db.relationship('Professional', back_populates='service')
    service_requests = db.relationship('ServiceRequest', back_populates='service', lazy=True)

    def __repr__(self):
        return f"Service('{self.name}', '{self.base_price}', '{self.estimated_duration}')"

class ServiceRequest(db.Model):
    """
    Model to store the service requests. 
    """
    __tablename__ = 'ServiceRequest'

    id = db.Column(db.Integer, primary_key=True)
    request_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp()) 
    appointment_date = db.Column(db.DateTime, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    special_instructions = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    # Foreign Keys
    customer_id = db.Column(db.Integer, db.ForeignKey('Customer.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('Service.id'), nullable=False)
    payment_type_id = db.Column(db.Integer, db.ForeignKey('PaymentType.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('RequestStatus.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('Professional.id'))

    # Relationships
    customer = db.relationship('Customer', back_populates='service_requests', lazy=True)
    service = db.relationship('Service', back_populates='service_requests', lazy=True)
    status = db.relationship('RequestStatus', back_populates='service_requests', lazy=True)
    payment_type = db.relationship('PaymentType', back_populates='service_requests', lazy=True)
    professional = db.relationship('Professional', back_populates='service_requests', lazy=True)
    ignore_logs = db.relationship('IgnoreLog', back_populates='service_request', lazy=True)
    customer_review = db.relationship('CustomerReview', back_populates='service_request', lazy=True)
    professional_review = db.relationship('ProfessionalReview', back_populates='service_request', lazy=True)

class RequestStatus(db.Model):
    """
    Model to store the lookup table of request statuses.\n
    Pending (1) - The app is trying to find a professional.
    Accepted (2) - A professional has accepted the service request.
    Terminated (3) - The service request has been closed by the customer before completion.
    Finished (4) - The service request has been successfully completed.
    Expired (5) - The service request has expired.
    """
    __tablename__ = 'RequestStatus'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, unique=True)

    # Relationships
    service_requests = db.relationship('ServiceRequest', back_populates='status', lazy=True)

class PaymentType(db.Model):
    """
    Model to store the lookup table of payment types.
    """
    __tablename__ = 'PaymentType'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False, unique=True)

    # Relationships
    service_requests = db.relationship('ServiceRequest', back_populates='payment_type', lazy=True)

class IgnoreLog(db.Model):
    """
    Table to log ignored service requests by professionals.
    """
    __tablename__ = 'IgnoreLog'
    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(db.Integer, db.ForeignKey('Professional.id'), nullable=False)
    service_request_id = db.Column(db.Integer, db.ForeignKey('ServiceRequest.id'), nullable=False)
    ignored_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    # Relationships
    professional = db.relationship('Professional', back_populates='ignore_logs', lazy=True)
    service_request = db.relationship('ServiceRequest', back_populates='ignore_logs', lazy=True)

class CustomerReview(db.Model):
    """
    Model to store reviews about the customers posted by professionals.
    """
    __tablename__ = 'CustomerReview'
    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('ServiceRequest.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('Professional.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customer.id'), nullable=False)
    rating = db.Column(db.Float, nullable=True)
    review = db.Column(db.Text, nullable=True)
    report = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Relationships
    service_request = db.relationship('ServiceRequest', back_populates='customer_review', lazy=True)
    professional = db.relationship('Professional', back_populates='customer_review', lazy=True)
    customer = db.relationship('Customer', back_populates='reviews_received', lazy=True)

class ProfessionalReview(db.Model):
    """
    Model to store reviews about the professionals posted by customers.
    """
    __tablename__ = 'ProfessionalReview'
    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('ServiceRequest.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customer.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('Professional.id'), nullable=False)
    rating = db.Column(db.Float, nullable=True)
    review = db.Column(db.Text, nullable=True)
    report = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    service_request = db.relationship('ServiceRequest', back_populates='professional_review', lazy=True)
    customer = db.relationship('Customer', back_populates='professional_review', lazy=True)
    professional = db.relationship('Professional', back_populates='reviews_received', lazy=True)

# Lookup Tables - SQLite does not support Enums
class UserRole(db.Model):
    """
    Model to store the lookup table of user roles.\n
    Admin (0).\n
    Customer (1).\n 
    Professional (2).\n
    """
    __tablename__ = 'UserRole'
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), unique=True, nullable=False)

    # Relationships
    users = db.relationship('User', back_populates='role', lazy=True)

class City(db.Model):
    """
    Model to store the lookup table for cities.
    """
    __tablename__ = 'City'
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(20), unique=True, nullable=False)

    # Foreign Keys
    # state_id = db.Column(db.Integer, db.ForeignKey('State.id'))

    # Relationships
    zipcodes = db.relationship('Zipcode', back_populates='city', lazy=True)

class Zipcode(db.Model):
    """
    Model to store the lokup table for zipcodes.
    """
    __tablename__ = 'Zipcode'
    id = db.Column(db.Integer, primary_key=True)
    zipcode = db.Column(db.String(6), unique=True, nullable=False)

    # Foreign Keys
    city_id = db.Column(db.Integer, db.ForeignKey('City.id'))

    # Realtionships
    city = db.relationship('City', back_populates='zipcodes', lazy=True)
    customers = db.relationship('Customer', back_populates='zipcode', lazy=True)
    professionals = db.relationship('Professional', back_populates='zipcode', lazy=True)
    services = db.relationship('Service', secondary=zipcode_service, back_populates='zipcodes', passive_deletes=True)
