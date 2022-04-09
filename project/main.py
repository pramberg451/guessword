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

def get_new_word():
    word = random.choice(open("project/nouns.txt").readlines()).strip()
    return word

def get_possible_hints(word):
    base_url = "http://ngrams.ucd.ie/therex3/common-nouns/member.action?member={term}&kw={term}&needDisamb=false&xml=true"
    query = base_url.format(term=word)
    response = requests.get(query)
    json_string = json.dumps(xmltodict.parse(response.content))
    data = json.loads(json_string)

    categories = []
    for category in data['MemberData']['Categories']['Category']:
        if int(category['@weight']) > 50:
            categories.append(category)
    
    return categories

def get_new_hint():
    if session['possible_hints']:
        category = random.choice(session['possible_hints'])
        descriptors = category['#text'].split(':')
        hint = "".join(["The answer is a ", descriptors[0], " ", descriptors[1], "."])
    else:
        hint = 0
    return hint

def get_comparative_hint(word):
    base_url = "http://ngrams.ucd.ie/therex3/common-nouns/share.action?word1={word1}&word2={word2}&xml=true"
    query = base_url.format(word1 = session['answer'], word2 = word)
    response = requests.get(query)
    json_string = json.dumps(xmltodict.parse(response.content))
    data = json.loads(json_string)
        
    categories = []
    if len(data['SharedCategory']['Members']) > 2:
        for category in data['SharedCategory']['Members']['Member']:
            #print(category)
            if int(category['@weight']) > 50:
                categories.append(category)
    if categories:    
        category = random.choice(categories)
        descriptors = category['#text'].split(':')
        hint = "".join(["The answer" + " and " + word + " are both ", descriptors[0], " ", descriptors[1], "s."])
    else:
        hint = 0
    return hint

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
        # Get a new word to guess and its Thesaurus Rex data
        session['answer'] = get_new_word()
        session['possible_hints'] = get_possible_hints(session['answer'])
        
        # Get an initial hint
        list = []
        list.append(get_new_hint())
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
    
        # If guess was incorrect
        else:
            # Get similarity between the guess and the answer and add to the list
            similarity = get_similarity(session['answer'], new_guess)
            list = session['guesses']
            list.append([new_guess, similarity])
            session['guesses'] = list

            # If another normal hint is possible (MAX 3)
            if len(session.get('hints')) < 3:
                hint = get_new_hint()
                # If hint exists and its not a repeat add it to the hint list
                if hint and hint not in session['hints']:
                    list = session['hints']
                    list.append(hint)
                    session['hints'] = list
                
                if current_user.is_authenticated:
                    current_user.total_hints += 1
            
            # If another comparative hint is possible (MAX 2)
            elif len(session.get('hints')) < 5 or (len(session['possible_hints']) == len(session['hints'])):
                # Get a comparative hint for each guess and if its vaild append it
                comparative_hints = []
                for guess in session['guesses']:
                    comparative_hint = get_comparative_hint(guess[0])
                    if comparative_hint:
                        comparative_hints.append(comparative_hint)
                
                # If there were any valid comparative hints choose a random one and add it to the hint list if its not a repeat
                if comparative_hints:
                    hint = random.choice(comparative_hints)
                    if hint not in session['hints']:
                        list = session['hints']
                        list.append(hint)
                        session['hints'] = list

                if current_user.is_authenticated:
                    current_user.total_hints += 1
    
    # If it wasn't a guess then it was a forfeit
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
