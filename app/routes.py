from app import app, db, bcrypt
from app.forms import (
    AcceptRequestForm,
    CloseRequestForm,
    CustomerDetailsForm,
    EditRequestForm,
    IgnoreRequestForm,
    ProfessionalDetailsForm,
    LoginForm,
    CategoryForm,
    ProfessionalRejectForm,
    ProfessionalVerifyForm,
    ServiceForm,
    ServiceRequestForm,
    DeleteForm,
    ProfessionalZipcodeForm,
    ResubmitProfessionalDetailsForm,
    TerminateRequestForm,
)
from app.models import (
    CustomerReview,
    IgnoreLog,
    PaymentType,
    ProfessionalReview,
    RequestStatus,
    ServiceRequest,
    User,
    UserRole,
    Customer,
    Zipcode,
    Category,
    Service,
    Professional,
    Customer,
    ScrutinyRequest,
    ScrutinyStatus,
)
from app.utils import roles_accepted, forbid_admins_professionals, save_img, save_pdf
from flask import make_response
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import func
from flask import render_template, flash, url_for, request, redirect, abort
from flask_login import login_user, logout_user, login_required, current_user
import os
import plotly.express as px
import plotly.io as pio

"""
How data POSTed from the user gets into a Flask-WTF form object?

"""
# Enums -------------------------------------------------------------------------------------------
class Role(Enum):
    """
    Enum classes for user roles.
    """
    GUEST = "Guest"
    CUSTOMER = "Customer"
    PROFESSIONAL = "Professional"
    ADMIN = "Admin"

class ServiceRequestEnum(Enum):
    """
    Enum classes for service request types.
    """
    PENDING = "Pending"
    SCHEDULED = "Scheduled"
    TERMINATED = "Terminated"
    FINISHED = "Finished"
    EXPIRED = "Expired"

class ScrutinyStatusEnum(Enum):
    """
    Enums for Professional application's scrutiny status types.
    """
    PENDING = "Pending"
    REJECTED = "Rejected"
    BLOCKED = "Blocked"
    VERIFIED = "Verified"

# Authentiation -----------------------------------------------------------------------------------
@app.route("/signup/customer", methods=["POST", "GET"])
def signup_customer():
    form = CustomerDetailsForm()
    if form.validate_on_submit():
        try:
            customer_role_id = (UserRole.query.filter_by(role=Role.CUSTOMER.value).first().id)
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
            user = User(email=form.email.data, password=hashed_password, role_id=customer_role_id,)
            customer = Customer(first_name=form.first_name.data,
                                last_name=form.last_name.data,
                                dob=form.dob.data,
                                phone=form.phone.data,
                                address=form.address.data,
                                zipcode_id=form.zipcode.data)
            customer.user = user

            db.session.add(user)
            db.session.add(customer)

            db.session.commit()

            flash("Customer registered successfully!", "success")
            return redirect(url_for("login"))

        except Exception as error:
            db.session.rollback()
            flash(f"Error: {str(error)}", "danger")
            print(">>> SIGNUP ERROR:", error)

    return render_template("signup_customer.html", form=form)

@app.route("/signup/professional/zipcode", methods=["GET", "POST"])
def signup_professional_zipcode():
    role=Role.GUEST.value
    zipcodes = Zipcode.query.all()
    form = ProfessionalZipcodeForm()
    if form.validate_on_submit():
        zipcode = form.zipcode.data
        zipcode_number = (Zipcode.query.filter_by(id=zipcode).first()).zipcode
        return redirect(url_for("signup_professional_details", zipcode_number=zipcode_number))
    return render_template("signup_professional_zipcode.html", form=form, zipcodes=zipcodes, role=role)

@app.route("/signup/professional/details/<string:zipcode_number>", methods=["GET", "POST"])
def signup_professional_details(zipcode_number):
    role=Role.GUEST.value
    zipcodes = Zipcode.query.all()
    zipcode = Zipcode.query.filter_by(zipcode=zipcode_number).first()
    if zipcode == None:
        flash("Please select a valid zipcode from the list before proceeding!", "danger")
        return redirect(url_for("signup_professional_zipcode"))

    else:
        form = ProfessionalDetailsForm(selected_zipcode=zipcode.id)

        if form.validate_on_submit():
            try:
                identifier = (form.email.data).split("@")[0]
                profile_filename = f"{app.config['UPLOAD_PROFESSIONAL_PROFILE']}/prof_profile_{identifier}{os.path.splitext((form.image.data).filename)[1]}"
                id_filename = f"{app.config['UPLOAD_PROFESSIONAL_ID']}/prof_id_{identifier}{os.path.splitext((form.id_proof.data).filename)[1]}"
                resume_filename = f"{app.config['UPLOAD_PROFESSIONAL_RESUME']}/prof_resume_{identifier}{os.path.splitext((form.resume.data).filename)[1]}"

                professional_role_id = (
                    UserRole.query.filter_by(role=Role.PROFESSIONAL.value).first().id
                )
                hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
                user = User(email=form.email.data, password=hashed_password, role_id=professional_role_id,)
                professional = Professional(first_name=form.first_name.data,
                                            last_name=form.last_name.data,
                                            dob=form.dob.data,
                                            phone=form.phone.data,
                                            address=form.address.data,
                                            about=form.about.data,
                                            experience=form.experience.data,
                                            profile_img=profile_filename,
                                            id_proof=id_filename,
                                            resume=resume_filename,
                                            zipcode_id=zipcode.id,
                                            service_id=form.service_id.data,)
                professional.user = user

                pending_status = ScrutinyStatus.query.filter_by(status=ServiceRequestEnum.PENDING.value).first()
                scrutiny_request = ScrutinyRequest(
                    professional=professional,
                    status_id=pending_status.id,
                    comments="Thank you for your application. We're currently reviewing it and will notify you of the outcome within 2-3 business days.",
                )

                db.session.add(user)
                db.session.add(professional)
                db.session.add(scrutiny_request)

                save_img(file=form.image.data, filename=profile_filename)
                save_pdf(file=form.id_proof.data, filename=id_filename)
                save_pdf(file=form.resume.data, filename=resume_filename)

                db.session.commit()

                flash("Professional registered successfully!", "success")
                flash("Your application is under scrutiny!", "info")
                return redirect(url_for("login"))

            except Exception as error:
                db.session.rollback()
                flash(f"Error: {str(error)}", "danger")
                print(">>> SIGNUP ERROR:", error)

        return render_template("signup_professional_details.html", zipcodes=zipcodes, form=form, role=role)

@app.route("/login", methods=["POST", "GET"])
def login():
    zipcodes = Zipcode.query.all()
    role=Role.GUEST.value
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"Login Successful. Hi {current_user.email}!.", "success")

            if (current_user.role_id== UserRole.query.filter_by(role=Role.ADMIN.value).first().id):
                return redirect(url_for("dashboard_admin"))

            elif (current_user.role_id== UserRole.query.filter_by(role=Role.PROFESSIONAL.value).first().id):
                return redirect(url_for("dashboard_professional"))

            return redirect(url_for("home"))
        
        flash("Login Unsuccessful. Please check credentials.", "danger")
    return render_template("login.html", form=form, zipcodes=zipcodes, role=role)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# Guests & Customers ------------------------------------------------------------------------------

# Home page does not require a login. A non registered user can also
# view the service that the app provides along with the search
# functionality. Professionals and admins are forbidden to access this
# route by a decorator.
@app.route("/", methods=["POST", "GET"])
@forbid_admins_professionals
def home():
    if current_user.is_authenticated: 
        role = Role.CUSTOMER.value 
        # Fetching all categories and services (through categories)
        categories = Category.query.all()
        return render_template("home.html", categories=categories, role=role)
    
    else:
        zipcodes = Zipcode.query.all()
        role = Role.GUEST.value
        categories = Category.query.all()
        return render_template("home.html", categories=categories, role=role, zipcodes=zipcodes)

# Clicking upon any service on the home page leads to the service's
# info page. Through the info page, a user can take a look to at what
# has been offered through the service and accordingly schedule an
# appointment if need be. Till this point the user need not be registered
# with the application, but as soon as they try to book the service, they
# will be asked to register to the application if not done already, after
# which they will be redirected to their profile page. Professionals and
# admins are forbidden to access this route by a decorator.
@app.route("/service-request/<int:service_id>", methods=["POST", "GET"])
@forbid_admins_professionals
def service_request(service_id):
    role = Role.CUSTOMER.value if current_user.is_authenticated else Role.GUEST.value
    zipcodes = Zipcode.query.all()
    form = ServiceRequestForm(payment_type_id=PaymentType.query.filter_by(type="Cash").first().id)
    service = Service.query.filter_by(id=service_id).first()
    
    if not service:
        flash("Invalid service selected.", "danger")
        return redirect(url_for('home'))

    if form.validate_on_submit():
        # If the user is a registered customer - request gets registered
        if current_user.is_authenticated:
            customer = Customer.query.filter_by(user_id=current_user.id).first()

            if not service:
                flash("Invalid service selected.", "danger")
                return redirect(url_for("service_request"))

            request_date = datetime.now()
            expiry_date = request_date + timedelta(minutes=15)
            # expiry_date = form.appointment_date.data - timedelta(minutes=15)

            new_request = ServiceRequest(
                customer_id=customer.id,
                service_id=service_id,
                appointment_date=form.appointment_date.data,
                request_date=request_date,
                expiry_date=expiry_date,
                special_instructions=form.special_instructions.data,
                status_id=RequestStatus.query.filter_by(status=ServiceRequestEnum.PENDING.value).first().id,
                payment_type_id=request.form.get("payment_type"))

            db.session.add(new_request)
            db.session.commit()

            flash("Service request submitted successfully!", "success")
            return redirect(url_for("home"))

        else:  # If the user is a guest - redirected to the login endpoint
            flash("Please login before making any requests.", "warning")
            return redirect(url_for("login"))

    return render_template("service_request.html", form=form, service=service, zipcodes=zipcodes, role=role)

@app.route("/search/guest", methods=["POST"])
@forbid_admins_professionals
def search_guest():
    role=Role.GUEST.value
    zipcode = request.form.get("zipcode", "").strip()
    service_name = request.form.get("service", "").strip()
    print(zipcode, service_name)

    if not zipcode or not service_name:
        flash("Please enter zipcode and service name both!", "warning")
        return redirect(request.referrer)

    # Fetch services in the given zipcode
    services = Service.query.join(Zipcode, Service.zipcodes).join(ServiceRequest).filter(
        Zipcode.zipcode == str(zipcode),
        Service.name.ilike(f"%{service_name}%")).all()
    print(services)

    return render_template("search_services.html", 
                           services=services, 
                           zipcode=zipcode, 
                           service_name=service_name,
                           role=role)

# Customer Routes ---------------------------------------------------------------------------------
@app.route("/customer/dashboard", methods=["GET"])
@login_required
@roles_accepted(Role.CUSTOMER.value)
def dashboard_customer():
    role=Role.CUSTOMER.value
    close_form = CloseRequestForm()
    terminate_form = TerminateRequestForm()
    customer = Customer.query.filter_by(id=current_user.customer[0].id).first()

    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for("login"))

    pending_requests = ServiceRequest.query.filter(
        ServiceRequest.customer_id == customer.id,
        ServiceRequest.status_id == RequestStatus.query.filter_by(status=ServiceRequestEnum.PENDING.value
                                                                  ).first().id,
                                                                  ).all()

    upcoming_appointments = ServiceRequest.query.filter(
        ServiceRequest.customer_id == customer.id,
        ServiceRequest.status_id == RequestStatus.query.filter_by(status=ServiceRequestEnum.SCHEDULED.value
                                                                  ).first().id,
                                                                  ).all()

    previous_appointments = ServiceRequest.query.filter(
        ServiceRequest.customer_id == customer.id,
        ServiceRequest.status_id.in_([RequestStatus.query.filter_by(status=ServiceRequestEnum.EXPIRED.value).first().id,
                                      RequestStatus.query.filter_by(status=ServiceRequestEnum.FINISHED.value).first().id,
                                      RequestStatus.query.filter_by(status=ServiceRequestEnum.TERMINATED.value).first().id])
                                      ).order_by(ServiceRequest.appointment_date.desc()).all()

    return render_template("dashboard_customer.html",
                           close_form=close_form,
                           terminate_form=terminate_form,
                           pending_requests=pending_requests,
                           upcoming_appointments=upcoming_appointments,
                           previous_appointments=previous_appointments,
                           role=role)

@app.route("/customer/edit-request/<int:request_id>", methods=["GET", "POST"])
@login_required
@roles_accepted(Role.CUSTOMER.value)
def edit_pending_request(request_id):
    try:
        role=Role.CUSTOMER.value
        form = EditRequestForm()
        service_request = ServiceRequest.query.filter_by(id=request_id, customer_id=current_user.customer[0].id).first()
        
        if (not service_request or service_request.status.status != ServiceRequestEnum.PENDING.value):
            flash("Invalid request or request is not editable.", "danger")
            return redirect(url_for("customer_dashboard"))
        
        if request.method=="POST":
            if form.validate_on_submit():
                service_request.request_date = datetime.now()
                service_request.appointment_date = form.appointment_date.data
                service_request.expiry_date = datetime.now() + timedelta(minutes=15)
                service_request.special_instructions = form.special_instructions.data
                service_request.payment_type_id = form.payment_type.data
                db.session.commit()

                flash("Service request updated successfully.", "success")
                return redirect(url_for("dashboard_customer"))
            else:
                flash("Failed to update the service request. Please check the form for errors.", "danger")
                return render_template("service_request_edit.html", form=form, role=role)
            
        elif request.method=="GET":
            form = EditRequestForm(payment_type=service_request.payment_type.id)
            form.appointment_date.data = service_request.appointment_date
            form.special_instructions.data = service_request.special_instructions
            return render_template("service_request_edit.html", form=form, role=role)
        
        else: 
            flash("Form submission failed. Please check your inputs.", "danger")
            return redirect(url_for("dashboard_customer"))
    
    except Exception as error:
        db.session.rollback()
        flash(f"Error: {str(error)}", "danger")
        print(">>> ERROR:", error)
        return redirect(url_for("dashboard_customer"))

@app.route("/customer/terminate-request/<int:request_id>", methods=["POST"])
@login_required
@roles_accepted(Role.CUSTOMER.value)
def terminate_request(request_id):
    try:
        service_request = ServiceRequest.query.filter_by(id=request_id, customer_id=current_user.customer[0].id).first()

        if not service_request or service_request.status.status not in [
            ServiceRequestEnum.PENDING.value,
            ServiceRequestEnum.SCHEDULED.value]:
            flash("Invalid request or request cannot be terminated.", "danger")
            return redirect(url_for("dashboard_customer"))

        # Termination is only allowed until 15 minutes from appointment_date for scheduled appointments
        if (service_request.status.status == ServiceRequestEnum.SCHEDULED.value
            and datetime.now() > (service_request.appointment_date - timedelta(minutes=15))):
            flash("You cannot terminate this request within 15 minutes of the appointment.", "warning")
            return redirect(url_for("dashboard_customer"))

        form = TerminateRequestForm()

        if form.validate_on_submit():
            service_request.status_id = (RequestStatus.query.filter_by(status=ServiceRequestEnum.TERMINATED.value
                                                                       ).first().id)
            db.session.commit()
            flash("Service request terminated successfully.", "success")
    
        else:flash("Failed to validate the termination request form.", "danger")

        return redirect(url_for("dashboard_customer"))
    
    except Exception as error:
        db.session.rollback()
        flash(f"Error: {str(error)}", "danger")
        print(">>> ERROR:", error)
        return redirect(url_for("dashboard_customer"))

@app.route("/customer/close-request/<int:request_id>", methods=["POST"])
@login_required
@roles_accepted(Role.CUSTOMER.value)
def close_request_customer(request_id):
    try:
        service_request = ServiceRequest.query.filter_by(
            id=request_id, customer_id=current_user.customer[0].id
        ).first()

        if datetime.now() < service_request.appointment_date:
            flash("You can only close requests after the appointment time.", "warning")
            return redirect(url_for("dashboard_customer"))

        if not service_request:
            flash("Invalid request or request not found.", "danger")
            return redirect(url_for("dashboard_customer"))

        form = CloseRequestForm()
        if form.validate_on_submit():
            # Adding the review made by customer about the professional
            review = ProfessionalReview(
                service_request_id=service_request.id,
                professional_id=service_request.professional_id,
                customer_id=current_user.customer[0].id,
                rating=form.rating.data,
                review=form.review.data,
                report=form.report.data,
            )

            if form.report.data:
                service_request.professional.user.reports = service_request.professional.user.reports + 1
                db.session.add(service_request.professional.user)
            db.session.add(review)
            db.session.commit()

            flash("Review submitted successfully.", "success")
            return redirect(url_for("dashboard_customer"))
        else:
            # If form validation fails
            flash("Failed to submit the review. Please check your inputs.", "danger")
            return redirect(url_for("dashboard_customer"))

    except Exception as error:
        # Rollback the session in case of an exception
        db.session.rollback()
        flash(f"An error occurred: {str(error)}", "danger")
        print(">>> ERROR:", str(error))
        return redirect(url_for("dashboard_customer"))

@app.route("/search/customer", methods=["POST"])
@roles_accepted(Role.CUSTOMER.value)
def search_customer():
    role = Role.CUSTOMER.value
    service_name = request.form.get("service", "").strip()

    if not service_name:
        flash("Please enter a service name!", "warning")
        return redirect(request.referrer)

    # Fetch services in the given zipcode
    services = Service.query.join(Zipcode, Service.zipcodes).join(ServiceRequest).filter(
        Zipcode.id == str(current_user.customer[0].zipcode_id),
        Service.name.ilike(f"%{service_name}%")).all()
    print(services)

    return render_template("search_services.html", 
                           services=services, 
                           service_name=service_name, 
                           role=role)

# Professional Routes -----------------------------------------------------------------------------
@app.route("/professional/dashboard", methods=["GET", "POST"])
@login_required
@roles_accepted(Role.PROFESSIONAL.value)
def dashboard_professional():
    role=Role.PROFESSIONAL.value
    professional = Professional.query.filter_by(user_id=current_user.id).first()
    scrutiny_request = (
        ScrutinyRequest.query.filter_by(professional_id=professional.id)
        .order_by(ScrutinyRequest.time.desc()).first())

    if scrutiny_request.status.status == ServiceRequestEnum.PENDING.value:
        return render_template("dashboard_professional.html", 
                               status=ScrutinyStatusEnum.PENDING.value, 
                               role=role)

    elif scrutiny_request.status.status == ScrutinyStatusEnum.REJECTED.value:
        resubmit_form = ResubmitProfessionalDetailsForm()
        if request.method == "POST" and resubmit_form.validate_on_submit():
            pending_status_id = (ScrutinyStatus.query.filter_by(status=ServiceRequestEnum.PENDING.value).first().id)
            new_request = ScrutinyRequest(professional_id=professional.id, status_id=pending_status_id)
            db.session.add(new_request)

            identifier = (professional.user.email).split("@")[0]
            profile_filename = f"{app.config['UPLOAD_PROFESSIONAL_PROFILE']}/prof_profile_{identifier}{os.path.splitext((resubmit_form.image.data).filename)[1]}"
            id_filename = f"{app.config['UPLOAD_PROFESSIONAL_ID']}/prof_id_{identifier}{os.path.splitext((resubmit_form.id_proof.data).filename)[1]}"
            resume_filename = f"{app.config['UPLOAD_PROFESSIONAL_RESUME']}/prof_resume_{identifier}{os.path.splitext((resubmit_form.resume.data).filename)[1]}"

            save_img(file=resubmit_form.image.data, filename=profile_filename)
            save_pdf(file=resubmit_form.id_proof.data, filename=id_filename)
            save_pdf(file=resubmit_form.resume.data, filename=resume_filename)

            db.session.commit()

            flash("Resubmission done successfully!", "success")
            return redirect(url_for("dashboard_professional"))

        return render_template("dashboard_professional.html",
                               status=ScrutinyStatusEnum.REJECTED.value,
                               form=resubmit_form,
                               comments=scrutiny_request.comments,
                               role=role
        )

    elif scrutiny_request.status.status == ScrutinyStatusEnum.VERIFIED.value:
        if professional.is_blocked:
            return render_template("dashboard_professional.html", 
                                   status=ScrutinyStatusEnum.BLOCKED.value,
                                   role=role)
        
        close_form = CloseRequestForm()
        ignore_form = IgnoreRequestForm()
        accept_form = AcceptRequestForm()

        service_requests = ServiceRequest.query.filter(
            ServiceRequest.id.not_in(
                db.session.query(IgnoreLog.service_request_id
                                 ).filter_by(professional_id=current_user.professional[0].id)),
            ServiceRequest.status.has(status=ServiceRequestEnum.PENDING.value),
            ServiceRequest.service_id == professional.service_id,
            ServiceRequest.customer.has(zipcode_id=professional.zipcode_id),
        ).all()

        upcoming_appointments = ServiceRequest.query.filter(
            ServiceRequest.professional_id == professional.id,
            ServiceRequest.status_id == RequestStatus.query.filter_by(status=ServiceRequestEnum.SCHEDULED.value).first().id,
        ).order_by(ServiceRequest.appointment_date).all()

        service_history = ServiceRequest.query.filter(
            ServiceRequest.professional_id == professional.id,
            ServiceRequest.status_id != RequestStatus.query.filter_by(status=ServiceRequestEnum.SCHEDULED.value).first().id,
        ).order_by(ServiceRequest.appointment_date.desc()).all()

        return render_template(
            "dashboard_professional.html",
            status=ScrutinyStatusEnum.VERIFIED.value,
            service_requests=service_requests,
            upcoming_appointments=upcoming_appointments,
            service_history=service_history,
            close_form=close_form,
            ignore_form=ignore_form,
            accept_form=accept_form,
            role=role
        )

    flash("Unable to determine professional status.", "danger")
    return redirect(url_for("logout"))

@app.route("/professional/accept-request/<int:request_id>", methods=["POST"])
@login_required
@roles_accepted(Role.PROFESSIONAL.value)
def accept_service_request(request_id):
    professional = Professional.query.filter_by(
        id=current_user.professional[0].id).first()
    service_request = ServiceRequest.query.get(request_id)

    if not professional:
        flash("You are not authorized to perform this action.", "danger")
        return redirect(url_for("dashboard_professional"))

    if not service_request:
        flash("Service request not found.", "danger")
        return redirect(url_for("dashboard_professional"))

    if (service_request.customer.zipcode.zipcode != professional.zipcode.zipcode
        or service_request.service_id != professional.service_id):
        flash("This service request is not in your designated area or service category.", "danger",)
        return redirect(url_for("dashboard_professional"))

    if service_request.status.status in [ServiceRequestEnum.SCHEDULED.value,
                                         ServiceRequestEnum.TERMINATED.value,
                                         ServiceRequestEnum.EXPIRED.value,
                                         ServiceRequestEnum.FINISHED.value]:
        flash(f"This service request has already been {service_request.status.status}.", "warning")
        return redirect(url_for("dashboard_professional"))

    service_request.professional_id = professional.id
    service_request.status_id = (RequestStatus.query.filter_by(status=ServiceRequestEnum.SCHEDULED.value).first().id)
    db.session.commit()

    flash(f"Service request {service_request.id} scheduled successfully.", "success")
    return redirect(url_for("dashboard_professional"))

@app.route("/professional/ignore-request/<int:request_id>", methods=["POST"])
@login_required
@roles_accepted(Role.PROFESSIONAL.value)
def ignore_service_request(request_id):
    professional_id = current_user.professional[0].id
    service_request = ServiceRequest.query.get(request_id)

    if not service_request or not professional_id:
        flash("Invalid service request.", "danger")
        return redirect(url_for("dashboard_professional"))

    # Logging the ignored action
    ignore_log = IgnoreLog(professional_id=professional_id, service_request_id=service_request.id)
    db.session.add(ignore_log)
    db.session.commit()

    flash("Service request ignored successfully.", "info")
    return redirect(url_for("dashboard_professional"))

@app.route("/professional/close-request/<int:request_id>", methods=["POST"])
@login_required
@roles_accepted(Role.PROFESSIONAL.value)
def close_request_professional(request_id):
    try:
        service_request = ServiceRequest.query.filter_by(id=request_id, professional_id=current_user.professional[0].id).first()

        if not service_request or service_request.status.status != ServiceRequestEnum.SCHEDULED.value:
            flash("Invalid request or request cannot be closed.", "danger")
            return redirect(url_for("dashboard_professional"))

        if datetime.now() < service_request.appointment_date:
            flash("You can only close requests after the appointment time.", "warning")
            return redirect(url_for("dashboard_professional"))

        form = CloseRequestForm()
        if form.validate_on_submit():
            # Updating the status to FINISHED
            service_request.status_id = RequestStatus.query.filter_by(status=ServiceRequestEnum.FINISHED.value).first().id
            service_request.updated_at = datetime.now()

            print("Step 2")
            # Adding the review made by professional about the customer
            review = CustomerReview(
                service_request_id=service_request.id,
                customer_id=service_request.customer_id,
                professional_id=current_user.professional[0].id,
                rating=form.rating.data,
                review=form.review.data,
                report=form.report.data,
            )

            db.session.add(service_request)

            print("Step 4")
            if form.report.data:
                service_request.customer.user.reports += 1
                db.session.add(service_request.customer.user)
                print("Step 5")
            db.session.add(review)
            db.session.commit()
            flash("Request closed successfully.", "success")
            return redirect(url_for("dashboard_professional"))

        else:
            flash("Failed to close the request. Please check your inputs.", "danger")
            return redirect(url_for("dashboard_professional"))
    
    except Exception as error:
        db.session.rollback()
        flash(f"Error: {str(error)}", "danger")
        print(">>> ERROR:", str(error))
        return redirect(url_for("dashboard_professional"))

# Admin Routes ------------------------------------------------------------------------------------
@app.route("/admin/dashboard", methods=["POST", "GET"])
@login_required
@roles_accepted(Role.ADMIN.value)
def dashboard_admin():
    zipcodes = Zipcode.query.all()
    role=Role.ADMIN.value
    add_category_form = CategoryForm()
    add_service_form = ServiceForm()
    verify_form = ProfessionalVerifyForm()
    reject_form = ProfessionalRejectForm()
    services = Service.query.order_by(Service.created_at.desc()).all()
    categories = Category.query.order_by(Category.created_at.desc()).all()
    pending_status_id =  ScrutinyStatus.query.filter_by(status=ServiceRequestEnum.PENDING.value).first().id
    pending_requests = ScrutinyRequest.query.filter_by(status_id=pending_status_id).all()

    if request.method == "POST":
        form_name = request.form.get("form_name")
        try:
            if form_name == "add_category" and add_category_form.validate_on_submit():
                category_name = add_category_form.name.data
                category_description = add_category_form.description.data
                category = Category(name=category_name, description=category_description)
                db.session.add(category)
                db.session.commit()
                flash(f"Category '{category_name}' added successfully!", "success")
                return redirect(url_for("dashboard_admin"))

            elif form_name == "add_service" and add_service_form.validate_on_submit():
                service_name = add_service_form.name.data
                service_description = add_service_form.description.data
                service_base_price = add_service_form.base_price.data
                service_estimated_duration = add_service_form.estimated_duration.data
                service_category_id = add_service_form.category_id.data
                service_image = add_service_form.image.data
                selected_zipcodes = Zipcode.query.filter(Zipcode.id.in_(add_service_form.zipcodes.data)).all()

                if add_service_form.image.data:
                    # Creating a new filename (probable change in extension) for saving uploaded service image
                    filename = f"{app.config['UPLOAD_SERVICE_PROFILE']}/service_{service_name}{os.path.splitext((add_service_form.image.data).filename)[1]}"
                    save_img(file=service_image, filename=filename)

                    # Creating a new service object
                    service = Service(name=service_name,
                                      description=service_description,
                                      base_price=service_base_price,
                                      estimated_duration=service_estimated_duration,
                                      category_id=service_category_id,
                                      image=filename)
                else:
                    service = Service(name=service_name,
                                      description=service_description,
                                      base_price=service_base_price,
                                      estimated_duration=service_estimated_duration,
                                      category_id=service_category_id)

                service.zipcodes.extend(selected_zipcodes)
                db.session.add(service)
                db.session.commit()

                flash(f"Service '{service_name}' added successfully!", "success")
                return redirect(url_for("dashboard_admin"))

            elif form_name == "reject_form" and reject_form.validate_on_submit():
                request_id = request.form.get("request_id")
                scrutiny_request = ScrutinyRequest.query.get(request_id)
                if scrutiny_request:
                    scrutiny_request.status_id = (ScrutinyStatus.query.filter_by(status="Rejected").first().id)
                    scrutiny_request.comments = reject_form.comments.data

                    db.session.commit()
                    flash(f"Application for professional {scrutiny_request.professional.first_name} rejected successfully.",
                          "warning")

                else:flash("Scrutiny request not found.", "danger")
                return redirect(url_for("dashboard_admin"))

            elif form_name == "verify_form" and verify_form.validate_on_submit():
                request_id = request.form.get("request_id")
                scrutiny_request = ScrutinyRequest.query.get(request_id)
                if scrutiny_request:
                    scrutiny_request.status_id = ScrutinyStatus.query.filter_by(status="Verified").first().id
                    scrutiny_request.professional.is_verified = True

                    db.session.commit()
                    flash(f"Application for professional {scrutiny_request.professional.first_name} verified successfully.",
                          "success")

                else: flash("Scrutiny request not found.", "danger")
                return redirect(url_for("dashboard_admin"))

            else: flash("Form submission failed. Please check your inputs.", "danger")

        except Exception as error:
            db.session.rollback()
            flash(f"Error: {str(error)}", "danger")
            print(">>> SUBMISSION ERROR:", error)
    
    return render_template("dashboard_admin.html",
                           add_category_form=add_category_form,
                           add_service_form=add_service_form,
                           verify_form=verify_form,
                           reject_form=reject_form,
                           services=services,
                           categories=categories,
                           pending_requests=pending_requests,
                           zipcodes=zipcodes,
                           role=role)

@app.route("/admin/process-application/<int:request_id>", methods=["POST"])
@login_required
@roles_accepted(Role.ADMIN.value)
def process_application(request_id):
    scrutiny_request = ScrutinyRequest.query.get(request_id)

    if not scrutiny_request:
        flash("Scrutiny request not found.", "danger")
        return redirect(url_for("dashboard_admin"))

    try:
        action = request.form.get("action")

        if action == "verify":
            scrutiny_request.status_id = (ScrutinyStatus.query.filter_by(status="Verified").first().id)
            scrutiny_request.professional.is_verified = True
            db.session.commit()
            flash(f"Application for professional ID {scrutiny_request.professional_id} verified successfully.",
                  "success")

        elif action == "reject":
            comments = request.form.get("comments")
            if not comments:
                flash("Rejection comments are required.", "danger")
                return redirect(url_for("dashboard_admin"))

            scrutiny_request.status_id = (ScrutinyStatus.query.filter_by(status="Rejected").first().id)
            scrutiny_request.comments = comments
            db.session.commit()
            flash(f"Application for professional ID {scrutiny_request.professional_id} rejected successfully.",
                  "warning")

        else: flash("Invalid action.", "danger")

    except Exception as e:
        db.session.rollback()
        flash(f"Error processing application: {str(e)}", "danger")

    return redirect(url_for("dashboard_admin"))

@app.route("/admin/edit-service/<int:service_id>", methods=["POST", "GET"])
@login_required
@roles_accepted(Role.ADMIN.value)
def edit_service(service_id):
    zipcodes = Zipcode.query.all()
    role=Role.ADMIN.value
    service = Service.query.get(service_id)
    
    if not service:
        flash("Invalid Service!", "danger")
        return redirect(url_for('dashboard_admin'))
    
    form_edit = ServiceForm()
    form_delete = DeleteForm()

    current_image_filename = service.image

    if request.method == "POST":
        form_name = request.form.get("form_name")

        if form_name == "edit_service" and form_edit.validate_on_submit():
            try:
                service.name = form_edit.name.data
                service.description = form_edit.description.data
                service.base_price = form_edit.base_price.data
                service.estimated_duration = form_edit.estimated_duration.data
                service.category_id = form_edit.category_id.data
                selected_zipcodes = Zipcode.query.filter(Zipcode.id.in_(form_edit.zipcodes.data)).all()
                service.zipcodes = selected_zipcodes

                if form_edit.image.data:
                    filename = f"{app.config['UPLOAD_SERVICE_PROFILE']}/service_{service.name}{os.path.splitext((form_edit.image.data).filename)[-1]}"
                    service.image = filename
                    db.session.commit()  # Committing changes to the database first
                    save_img(file=form_edit.image.data, filename=filename)

                else:
                    service.image = current_image_filename
                    db.session.commit()

                flash(f"Service '{service.name}' updated successfully!", "success")
                return redirect(url_for("dashboard_admin"))

            except Exception as error:
                db.session.rollback()
                flash(f"Error: {str(error)}", "danger")
                print(f">>> EDIT ERROR: {error}")

        elif form_name == "delete_service" and form_delete.validate_on_submit():
            try:
                db.session.delete(service)
                db.session.commit()
                flash(f"Service '{service.name}' deleted successfully!", "success")
                return redirect(url_for("dashboard_admin"))

            except Exception as error:
                db.session.rollback()
                flash(f"Error: {str(error)}", "danger")
                print(f">>> DELETE ERROR: {error}")

        else:
            flash("Invalid form details!", "danger")
            return redirect(url_for("dashboard_admin"))

    elif request.method == "GET":
        # form_edit = ServiceForm(category_id=service.category_id)
        form_edit.name.data = service.name
        form_edit.description.data = service.description
        form_edit.base_price.data = service.base_price
        form_edit.estimated_duration.data = service.estimated_duration
        form_edit.category_id.data = service.category_id
        form_edit.zipcodes.data = [zipcode.id for zipcode in service.zipcodes]

    return render_template("service_edit.html",
                           form_edit=form_edit,
                           form_delete=form_delete,
                           service=service,
                           zipcodes=zipcodes,
                           role=role)

@app.route("/admin/edit-category/<int:category_id>", methods=["POST", "GET"])
@login_required
@roles_accepted(Role.ADMIN.value)
def edit_category(category_id):
    zipcodes = Zipcode.query.all()
    role=Role.ADMIN.value
    category = Category.query.get(category_id)

    if not category:
        flash("Invalid Category!", "danger")
        return redirect(url_for('dashboard_admin'))
    
    form_edit = CategoryForm()
    form_delete = DeleteForm()

    if request.method == "POST":
        form_name = request.form.get("form_name")

        if form_name == "edit_category" and form_edit.validate_on_submit():
            try:
                category.name = form_edit.name.data
                category.description = form_edit.description.data
                db.session.commit()
                flash(f"Category '{category.name}' updated successfully!", "success")
                return redirect(url_for("dashboard_admin"))

            except Exception as error:
                db.session.rollback()
                flash(f"Error: {str(error)}", "danger")
                print(f">>> EDIT ERROR: {error}")

        elif form_name == "delete_category" and form_delete.validate_on_submit():
            try:
                db.session.delete(category)
                db.session.commit()
                flash(f"Service '{category.name}' deleted successfully!", "success")
                return redirect(url_for("dashboard_admin"))

            except Exception as error:
                db.session.rollback()
                flash(f"Error: {str(error)}", "danger")
                print(f">>> DELETE ERROR: {error}")

        else:
            flash("Invalid form details!", "danger")
            return redirect(url_for("dashboard_admin"))

    elif request.method == "GET":
        # form_edit = ServiceForm(category_id=service.category_id)
        form_edit.name.data = category.name
        form_edit.description.data = category.description

    return render_template("category_edit.html",
                           form_edit=form_edit,
                           form_delete=form_delete,
                           category=category,
                           zipcodes=zipcodes,
                           role=role)

@app.route("/admin/search-professionals", methods=["GET", "POST"])
@login_required
@roles_accepted(Role.ADMIN.value)
def search_admin():
    zipcodes = Zipcode.query.all()
    role=Role.ADMIN.value
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    zipcode = request.form.get("zipcode", "").strip()

    # Creating a base query
    query = Professional.query
    if name:
        query = query.filter(
            db.or_(
                Professional.first_name.ilike(f"%{name}%"),
                Professional.last_name.ilike(f"%{name}%")
            )
        )
    if email: query = query.join(User).filter(User.email.ilike(f"%{email}%"))
    if zipcode: query = query.join(Zipcode).filter(Zipcode.zipcode == zipcode)
    print(">>>", zipcode, email, name)

    professionals = query.all()
    # professionals = (Professional.query.join(Professional.user).order_by(User.reports.desc()).all())
    
    print(professionals)

    return render_template("search_professionals.html",
                           professionals=professionals,
                           input_name=name, input_email=email,
                           input_zipcode=zipcode, zipcodes=zipcodes,
                           role=role)

@app.route("/admin/block-professional/<int:professional_id>", methods=["POST"])
@login_required
@roles_accepted(Role.ADMIN.value)
def toggle_block_professional(professional_id):
    try:
        professional = Professional.query.get(professional_id)
        if not professional:
            flash("Invalid Professional")
            return redirect(request.referrer)

        # Toggling block status
        professional.is_blocked = not professional.is_blocked
        db.session.add(professional)
        db.session.commit()

        status = "unblocked" if not professional.is_blocked else "blocked"
        flash(f"Professional has been {status}.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}", "danger")

    return redirect(request.referrer or url_for("search_professionals"))

# def no_cache_response(template):
#     response = make_response(render_template(template))
#     # Add cache control headers to prevent caching by the browser
#     response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
#     response.headers['Pragma'] = 'no-cache'
#     response.headers['Expires'] = '0'
#     return response