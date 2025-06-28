from app import app, image_size
from PIL import Image
import os
from flask import current_app, abort, redirect, url_for, flash
from flask_login import current_user
from werkzeug.utils import secure_filename
from functools import wraps
from app.models import UserRole

"""
secure_filename is a function provided by the Werkzeug utility library, 
which is used by Flask. It's designed to ensure that filenames are secure 
and do not contain any malicious characters that could potentially be used 
to perform attacks such as directory traversal.
"""

USER_ROLES = {"Admin": 0, "Customer": 1, "Professional": 2}

# ----- Role Based Access Control -----
def roles_accepted(*roles):
    """
    Decorator that ensures the current_user has at least one of the accepted roles.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the role ids for the accepted roles
            role_ids = [USER_ROLES[role] for role in roles]
            
            # Check if current user's role_id matches any of the accepted role_ids
            if current_user.role_id not in role_ids:
                abort(403)  # Forbidden
            return func(*args, **kwargs)
        return wrapper
    return decorator

def forbid_admins_professionals(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # If user is not logged in, allow access
        if not current_user.is_authenticated:
            return func(*args, **kwargs)
        
        # If logged in as a customer, allow access
        if current_user.role_id==USER_ROLES["Customer"]:
            return func(*args, **kwargs)
        
        # Redirect logged-in professionals and admins
        if current_user.role_id==USER_ROLES["Admin"]:
            flash("Admins are not authroized to access this page!", "danger")
            return redirect(url_for('dashboard_admin'))
        elif current_user.role_id==USER_ROLES["Professional"]:
            flash("Professionals are not authroized to access this page!", "danger")
            return redirect(url_for('dashboard_professional'))
        
        abort(403)  # Catch-all forbidden
    return wrapper

# ---------- File Handling ------------
def save_img(file, filename):
    """
    Function to save an Image file.
    """
    if file:
        file_path = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'], filename)
        resized_img=Image.open(file)
        resized_img.thumbnail(image_size)
        resized_img.save(file_path)
        return file_path
    else:
        raise ValueError("No image provided!")
    return None

def save_pdf(file, filename):
    """
    Function to save a PDF file.
    """
    if file:
        file_path = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return file_path
    else:
        raise ValueError("No pdf provided!")
    return None

def read_uploaded_file(file):
    #function to read the contents of an uploaded text file
    if file:
        file_content = file.read().decode('utf-8')
        return file_content
    return None

# ------------- Algorithm --------------
# for reprompting the expired service to all the nearby zipcodes 
