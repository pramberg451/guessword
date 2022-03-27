from flask import Blueprint, render_template, request, session, flash
from flask_login import login_required, current_user
from . import db
import requests

main = Blueprint('main', __name__)

def get_new_hint():
    hint = 'This is a hint'
    return hint

def get_new_riddle():
    riddle = 'barnacle'
    return riddle

def get_similarity():
    similarity = 0.75
    return similarity

@main.route('/')
def index():
    # If this is the first riddle set up the session data
    if session.get('new_riddle') is None:
        session['new_riddle'] = True
        session['hints'] = []
        session['guesses'] = []
        session['riddle_completed'] = False
    
    # If a new riddle needs to be generated
    if session['new_riddle']:
        # Get a new word to guess
        session['answer'] = get_new_riddle()
        
        # Get an initial hint
        list = []
        list.append(get_new_hint())
        session['hints'] = list
        current_user.total_hints += 1

        # Clear the guesses and reset completion status
        session['guesses'] = []
        session['riddle_completed'] = False
    
    return render_template('index.html')

@main.route('/<int:is_guess>', methods=['POST'])
def index_post(is_guess):
    if is_guess:
        new_guess = request.form['guess']
        current_user.total_guesses += 1
    
        # If guess was correct
        if new_guess == session['answer']:
            flash('Answer found!')
            session['riddle_completed'] = True
            
            current_user.wins += 1
            current_user.streak += 1
        
        # If guess was a repeat
        elif any(new_guess in guess for guess in session['guesses']):
            flash('That has already been guessed.')
    
        # If guess was incorrect and not a repeat
        else:
            similarity = get_similarity()
            list = session['guesses']
            list.append([new_guess, similarity])
            session['guesses'] = list
        
            if len(session.get('hints')) < 4:
                list = session['hints']
                list.append(get_new_hint())
                session['hints'] = list
                
                current_user.total_hints += 1
    else:
        flash('The answer was ' + session['answer'] + ".")
        session['riddle_completed'] = True

        current_user.forfeits += 1
        current_user.streak = 0
    
    db.session.commit()
    return render_template('index.html')

@main.route('/stats')
@login_required
def stats():
    return render_template('stats.html', username=current_user.username)
