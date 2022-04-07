from flask import Blueprint, render_template, request, session, flash
from flask_login import login_required, current_user
from . import db
from .models import Word
from numpy import frombuffer, float32, sqrt
import requests
import random
import json
import xmltodict

main = Blueprint('main', __name__)

def get_new_hint(word):
    base_url = "http://ngrams.ucd.ie/therex3/common-nouns/member.action?member={term}&kw={term}&needDisamb=false&xml=true"
    query = base_url.format(term=word)
    response = requests.get(query)
    json_string = json.dumps(xmltodict.parse(response.content))
    data = json.loads(json_string)
    
    categories = []
    for category in data['MemberData']['Categories']['Category']:
        categories.append(category)

    hint = random.choice(categories)
    return hint

def get_new_word():
    word = random.choice(open("project/nouns.txt").readlines()).strip()
    return word

def square_rooted(x):
    return round(sqrt(sum([a*a for a in x])),3)

def cosine_similarity(x,y):
    numerator = sum(a*b for a,b in zip(x,y))
    denominator = square_rooted(x)*square_rooted(y)
    return round(numerator/float(denominator),3)

def get_similarity(answer, guess):
    word1 = Word.query.filter_by(word=answer).first()
    word1vector = frombuffer(word1.vector, float32)
    word2 = Word.query.filter_by(word=guess).first()
    word2vector = frombuffer(word2.vector, float32)
    
    similarity = cosine_similarity(word1vector, word2vector)
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
        session['answer'] = get_new_word()
        
        # Get an initial hint
        list = []
        list.append(get_new_hint(session['answer']))
        session['hints'] = list
        if current_user.is_authenticated:
            current_user.total_hints += 1

        # Clear the guesses and reset completion status
        session['guesses'] = []
        session['riddle_completed'] = False
    
    return render_template('index.html')

@main.route('/<int:is_guess>', methods=['POST'])
def index_post(is_guess):
    if is_guess:
        new_guess = request.form['guess'].lower()
        if current_user.is_authenticated:
            current_user.total_guesses += 1
    
        # If guess was correct
        if new_guess == session['answer']:
            flash('Answer found!')
            session['riddle_completed'] = True
            
            if current_user.is_authenticated:
                current_user.wins += 1
                current_user.streak += 1
        
        # If guess was a repeat
        elif any(new_guess in guess for guess in session['guesses']):
            flash('That has already been guessed.')
    
        # If guess was incorrect and not a repeat
        else:
            similarity = get_similarity(session['answer'], new_guess)
            list = session['guesses']
            list.append([new_guess, similarity])
            session['guesses'] = list
        
            if len(session.get('hints')) < 4:
                list = session['hints']
                list.append(get_new_hint(session['answer']))
                session['hints'] = list
                
                if current_user.is_authenticated:
                    current_user.total_hints += 1
    else:
        flash('The answer was ' + session['answer'] + ".")
        session['riddle_completed'] = True
        
        if current_user.is_authenticated:
            current_user.forfeits += 1
            current_user.streak = 0
    
    db.session.commit()
    return render_template('index.html')

@main.route('/stats')
@login_required
def stats():
    return render_template('stats.html', username=current_user.username)
