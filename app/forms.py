from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import (
    DateTimeField, DateTimeLocalField, FloatField, StringField, IntegerField, IntegerRangeField, EmailField, PasswordField, BooleanField,
    FileField, SelectField, SelectMultipleField, TextAreaField, SubmitField, DateField, TimeField, HiddenField
)
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired, Length, Email, ValidationError, EqualTo, NumberRange
from app.models import PaymentType, User, City, Zipcode, Category, Service
import string
from datetime import date, time, datetime, timedelta
import re

"""
It is recommended that the forms, in their definitions, should not 
execute something that involve other parts of the application like 
executing queries. It may lead to errors if the application is not
completely setup, especially the parts that are imported.

An example of this is when we try to populate a dynaminc select 
field choices by running database queries like Model.query(), in 
the 'choices: list' parameter of the field.
"""

"""
If we want the choices for select fields to be populated dynamically
from the entries of a model, then there are 2 ways to doing it - 
first, set empty choices for the flask-wtf form class attribute while
declaration, and populate them in the controller (views), by querying
the database, before sending the form through a GET request.

The second way is to set the choices in the __init__ method of the 
form class, by querying the database there.
"""

def validate_password(form, field):
    if ((len(field.data) < 8)
        | (len([char for char in field.data if char.isupper()]) < 1)
        | (len([char for char in field.data if char.islower()]) < 1)
        | (len([char for char in field.data if char in string.punctuation]) < 1)):
        raise ValidationError("""Password must be atleast 8 characters long, with atleast 
                              1 uppercase, 1 lowercase letters and 1 special character.""")

class CustomerDetailsForm(FlaskForm):
    """
    Signup form for a customer.
    """
    # account details - user model
    email = EmailField("Email", validators=[DataRequired(), Email()], render_kw={"placeholder": "Email", "required": True})
    password = PasswordField("Password", validators=[DataRequired(), validate_password], render_kw={"placeholder": "Password", "required": True})
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")], render_kw={"placeholder": "Retype Password", "required": True})
    
    # personal profile attributes - customer model
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=2, max=15)], render_kw={"placeholder": "First Name", "required": True})
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=2, max=15)], render_kw={"placeholder": "Last Name", "required": True})
    dob = DateField("Date of Birth", format="%Y-%m-%d", validators=[DataRequired()], render_kw={"placeholder": "YYYY-MM-DD", "required": True})
    phone = StringField("Phone", validators=[Length(min=10, max=10)])
    address = TextAreaField("Address", validators=[DataRequired(), Length(min=2, max=200)], render_kw={"placeholder": "Address", "required": True})
    zipcode = SelectField("Zipcode", choices=[], render_kw={"placeholder": "Zipcode", "required": True})
    submit = SubmitField("Register")

    def __init__(self, *args, **kwargs):
        super(CustomerDetailsForm, self).__init__(*args, **kwargs)
        self.zipcode.choices = [(str(zipcode.id), f"{zipcode.zipcode} ({zipcode.city.city})") for zipcode in Zipcode.query.all()]
        
    def validate_dob(self, dob):
        today = date.today()
        age = today.year - dob.data.year - ((today.month, today.day) < (dob.data.month, dob.data.day))
        if age < 18: raise ValidationError("You must be at least 18 years old.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user: raise ValidationError("This email is already registered.")

    # def validate_username(self, username):
    #     user = User.query.filter_by(username = username)
    #     if user:
    #         raise ValidationError('This username already exists.')
    #     # usernames are used in filenames, hence they cant have chars that are not
    #     # allowed in filenames in Windows
    #     disallowed_chars_pattern = r'[<>:"/\\|?*]'
    #     if re.search(disallowed_chars_pattern, username.data):
    #         raise ValidationError('Username cannot contain: <>:"/\\|?*')

class ProfessionalZipcodeForm(FlaskForm):
    """
    Step 1: Form to collect the professional's preferred zipcode.
    """
    zipcode = SelectField("Zipcode", choices=[], validators=[DataRequired()], render_kw={"required": True})
    submit = SubmitField("Next")

    def __init__(self, *args, **kwargs):
        super(ProfessionalZipcodeForm, self).__init__(*args, **kwargs)
        self.zipcode.choices = [(str(zipcode.id), f"{zipcode.zipcode} ({zipcode.city.city})") for zipcode in Zipcode.query.all()]

class ProfessionalDetailsForm(FlaskForm):
    """
    Step 2: Form to collect the professional's details.
    """
    # Account details - user model
    email = EmailField("Email", validators=[DataRequired(), Email()], render_kw={"required": True})
    password = PasswordField("Password", validators=[DataRequired(), validate_password], render_kw={"required": True})
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")], render_kw={"required": True})

    # Personal profile attributes - professional model
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=2, max=15)], render_kw={"required": True})
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=2, max=15)], render_kw={"required": True})
    image = FileField("Profile Image:", validators=[FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Images only!")], render_kw={"required": True})
    id_proof = FileField("ID Proof:", validators=[FileAllowed(["pdf"], "PDF only!")], render_kw={"required": True})
    resume = FileField("Resume:", validators=[FileAllowed(["pdf"], "PDF only!")], render_kw={"required": True})
    dob = DateField("Date of Birth", format="%Y-%m-%d", validators=[DataRequired()], render_kw={"required": True})
    phone = StringField("Phone", validators=[DataRequired(), Length(min=10, max=10)], render_kw={ "required": True},) 
    address = TextAreaField("Address", validators=[DataRequired(), Length(min=2, max=200)], render_kw={"required": True, "style": "height: 50px;"})
    service_id = SelectField("Service", choices=[], validators=[DataRequired()], render_kw={"required": True})

    # Professional profile attributes - professional model
    about = TextAreaField("About", validators=[DataRequired(), Length(min=2, max=500)], render_kw={"required": True, "style": "height: 50px;"})
    experience = FloatField("Experience (yrs)", validators=[DataRequired()], render_kw={"required": True})
    submit = SubmitField("Register")

    def __init__(self, selected_zipcode, *args, **kwargs):
        super(ProfessionalDetailsForm, self).__init__(*args, **kwargs)
        
        # Getting the list of services in the selected_zipcode
        services = (Zipcode.query.filter_by(id=selected_zipcode).first()).services
        self.service_id.choices = [(str(service.id), (f"{service.name} ({service.category.name if service.category else "NULL"})")) 
                                  for service in services]
        
    def validate_dob(self, dob):
        today = date.today()
        age = (today.year - dob.data.year - ((today.month, today.day) < (dob.data.month, dob.data.day)))
        if age < 18: raise ValidationError("You must be at least 18 years old.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user: raise ValidationError("This email is already registered.")

class ResubmitProfessionalDetailsForm(FlaskForm):
    """
    Step 2: Form to collect the professional's details.
    """

    # Personal profile attributes - professional model
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=2, max=15)], render_kw={"required": True})
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=2, max=15)], render_kw={"required": True})
    image = FileField("Profile Image:", validators=[FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Images only!")], render_kw={"required": True})
    id_proof = FileField("ID Proof:", validators=[FileAllowed(["pdf"], "PDF only!")], render_kw={"required": True})
    resume = FileField("Resume:", validators=[FileAllowed(["pdf"], "PDF only!")], render_kw={"required": True})
    dob = DateField("Date of Birth", format="%Y-%m-%d", validators=[DataRequired()], render_kw={"required": True})
    phone = StringField("Phone", validators=[DataRequired(), Length(min=10, max=10)], render_kw={ "required": True},) 
    address = TextAreaField("Address", validators=[DataRequired(), Length(min=2, max=200)], render_kw={"required": True, "style": "height: 50px;"})

    # Professional profile attributes - professional model
    experience = FloatField("Experience (yrs)", validators=[DataRequired()], render_kw={"required": True})
    submit = SubmitField("Submit")

    def validate_dob(self, dob):
        today = date.today()
        age = (today.year - dob.data.year - ((today.month, today.day) < (dob.data.month, dob.data.day)))
        if age < 18: raise ValidationError("You must be at least 18 years old.")

class LoginForm(FlaskForm):
    """
    Login form for all users.
    """
    email = EmailField("Email", validators=[DataRequired(), Email()], render_kw={"placeholder": "Email", "required": True})
    password = PasswordField("Password", validators=[DataRequired()], render_kw={"placeholder": "Password", "required": True})
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")

class CategoryForm(FlaskForm):
    """
    Service Category addition form for admins.
    """
    name = StringField("Category Name", validators=[DataRequired(), Length(min=10, max=30)], render_kw={"required": True})
    description = TextAreaField("Category Description (15 words)", validators=[DataRequired()], render_kw={"style": "height: 150px; width: 100%;"})
    submit = SubmitField("Submit")

class ServiceForm(FlaskForm):
    """
    Service addition/updation form for admins.
    """
    name = StringField("Service Name", validators=[DataRequired(), Length(min=10, max=30)], render_kw={"required": True})
    description = TextAreaField("Service Description", validators=[DataRequired()], render_kw={"style": "height: 250px; width: 100%;"})
    base_price = FloatField("Base Price", validators=[DataRequired()], render_kw={"required": True})
    estimated_duration = IntegerField("Est Duration (mins)", validators=[DataRequired()], render_kw={"required": True})
    category_id = SelectField("Category", choices=[], validators=[DataRequired()], render_kw={"required": True}, coerce=int)
    image = FileField('Upload Image', validators=[FileAllowed(['gif', 'jpg', 'png', 'webp'], 'Images only!')])
    zipcodes = SelectMultipleField('Zipcodes', validators=[DataRequired()], choices=[], render_kw={"required": True, "style": "height: 150px;"}, coerce=int)
    submit = SubmitField("Submit")

    def __init__(self, *args, **kwargs):
        super(ServiceForm, self).__init__(*args, **kwargs)
        # Querying the database for the list of cities
        self.category_id.choices = [(str(category.id), category.name) for category in Category.query.all()]
        self.zipcodes.choices = [(str(zipcode.id), f"{zipcode.zipcode} ({zipcode.city.city})") for zipcode in Zipcode.query.all()]

class ServiceRequestForm(FlaskForm):
    """
    Form for customers to create a service request.
    """

    min_date = ((datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M') if datetime.now().time() > time(18, 0) else (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'))
    appointment_date = DateTimeLocalField("Appointment Date", format='%Y-%m-%dT%H:%M', validators=[DataRequired()], render_kw={"required": True, "min": min_date, "value": min_date})
    payment_type = SelectField('Payment Type', validators=[DataRequired()], choices=[], render_kw={"required": True}, coerce=str)
    special_instructions = TextAreaField("Special Instructions", render_kw={"style": "height: 150px; width: 100%;"})
    submit = SubmitField("Request")

    def __init__(self, *args, **kwargs):
        super(ServiceRequestForm, self).__init__(*args, **kwargs)
        self.payment_type.choices = [(payment_type.id, payment_type.type) for payment_type in PaymentType.query.all()]

    def validate_appointment_date(form, field):
        """
        Validates that the appointment_date field does not have a 
        datetime of today after 6pm or datetime in the past.
        """
        # Get the current date and time
        current_date = date.today()
        current_time = datetime.now().time()
        cutoff_time = time(18, 0)

        if field.data.date() == current_date and current_time >= cutoff_time:
            raise ValidationError(
                "Appointments for today cannot be booked after 6 PM. Please select a future date."
            )
        
        elif (field.data - datetime.now()) < timedelta(hours=2):
            raise ValidationError("The appointment date must be atleast 2 hours from the current time.")

        elif field.data.date() < current_date:
            raise ValidationError("The appointment date cannot be in the past.")

class DeleteForm(FlaskForm):
    """
    A simple delete form.
    """
    submit = SubmitField("Delete")

class ProfessionalVerifyForm(FlaskForm):
    submit = SubmitField("Verify")

    # def __init__(self, request_id:int, *args, **kwargs):
    #     super(ProfessionalVerifyForm, self).__init__(*args, **kwargs)
    #     self.form_name.value = "verify_form"
    #     self.request_id.value = request_id

class ProfessionalRejectForm(FlaskForm):
    comments = TextAreaField("Rejection Comments", validators=[DataRequired()])
    submit = SubmitField("Reject")
 
    # def __init__(self, request_id:int, *args, **kwargs):
    #     super(ProfessionalRejectForm, self).__init__(*args, **kwargs)
    #     self.form_name.value = "reject_form"
    #     self.request_id.value = request_id

class EditRequestForm(FlaskForm):
    """
    Form for customers to edit a service request.
    """
    min_date = ((datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M') if datetime.now().time() > time(18, 0) else (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'))
    appointment_date = DateTimeLocalField("Appointment Date", format='%Y-%m-%dT%H:%M', validators=[DataRequired()], render_kw={"required": True, "min": min_date})
    payment_type = SelectField('Payment Type', validators=[DataRequired()], choices=[], render_kw={"required": True}, coerce=int)
    special_instructions = TextAreaField("Special Instructions", render_kw={"style": "height: 150px; width: 100%;"})
    submit = SubmitField("Update")

    def __init__(self, *args, **kwargs):
        super(EditRequestForm, self).__init__(*args, **kwargs)
        self.payment_type.choices = [(payment_type.id, payment_type.type) for payment_type in PaymentType.query.all()]

    def validate_appointment_date(form, field):
        """
        Validates that the appointment_date field does not have a 
        datetime of today after 6pm or datetime in the past.
        """
        # Get the current date and time
        current_date = date.today()
        current_time = datetime.now().time()
        cutoff_time = time(18, 0)

        if field.data.date() == current_date and current_time >= cutoff_time:
            raise ValidationError(
                "Appointments for today cannot be booked after 6 PM. Please select a future date."
            )
        
        elif (field.data - datetime.now()) < timedelta(hours=2):
            raise ValidationError("The appointment date must be atleast 2 hours from the current time.")

        elif field.data.date() < current_date:
            raise ValidationError("The appointment date cannot be in the past.")

class TerminateRequestForm(FlaskForm):
    submit = SubmitField("Terminate")

class AcceptRequestForm(FlaskForm):
    submit = SubmitField("Accept")

class IgnoreRequestForm(FlaskForm):
    submit = SubmitField("Ignore")

class CloseRequestForm(FlaskForm):
    rating = IntegerField("Rating", validators=[DataRequired(), 
                        NumberRange(min=0, max=5, message="Rate between 0 & 5")])
    review = TextAreaField("Review")
    report = BooleanField("Report User")
    submit = SubmitField("Close Request")
