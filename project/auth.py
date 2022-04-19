from flask import Blueprint, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user
from .models import User
from . import db

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    # Get info from the form
    username = request.form.get('username')
    password = request.form.get('password')

    # Check if the user exists
    user = User.query.filter_by(username=username).first()
    # If the user doesn't exist or the password doesn't match redirect w/ error message
    if not user or not check_password_hash(user.password, password):
        flash('Your username or password are incorrect.')
        return redirect(url_for('auth.login'))

    # Log in the user because the username and password were valid
    login_user(user)
    return redirect(url_for('main.index'))



@auth.route('/singup')
def signup():
    return render_template('signup.html')

@auth.route('/signup', methods=['POST'])
def signup_post():
    # Get info from form
    username = request.form.get('username')
    password = request.form.get('password')

    # Check if theres already a user with that name
    if User.query.filter_by(username=username).first():
        flash('An account with that username already exists')
        return redirect(url_for('auth.signup'))

    # Create new user with username, a hashed password, and blank stats
    new_user = User(username=username,
                    password=generate_password_hash(password, method='sha256'),
                    wins = 0,
                    forfeits = 0,
                    streak = 0,
                    total_hints = 0,
                    total_guesses = 0)

    # Add user to the database
    db.session.add(new_user)
    db.session.commit()
    
    return redirect(url_for('auth.login'))



@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
