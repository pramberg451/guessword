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

def get_trex_hint(word):
    base_url = "http://ngrams.ucd.ie/therex3/common-nouns/member.action?member={term}&kw={term}&needDisamb=false&xml=true"
    query = base_url.format(term=word)
    response = requests.get(query)
    json_string = json.dumps(xmltodict.parse(response.content))
    data = json.loads(json_string)
    
    categories = []
    if len(data['MemberData']['Categories']) > 1:
        for category in data['MemberData']['Categories']['Category']:
            if int(category['@weight']) > 25:
                categories.append(category)
    
    if categories:
        category = random.choice(categories)
        descriptors = category['#text'].split(':')
        hint = "".join(["I am a ", descriptors[0], " ", descriptors[1], "."])
    else:
        hint = 0
    return hint


def get_comparative_trex_hint(word1, word2):
    base_url = "http://ngrams.ucd.ie/therex3/common-nouns/share.action?word1={word1}&word2={word2}&xml=true"
    query = base_url.format(word1 = word1, word2 = word2)
    response = requests.get(query)
    json_string = json.dumps(xmltodict.parse(response.content))
    data = json.loads(json_string)
    categories = []
    if len(data['SharedCategory']['Members']) > 2:
        members = data['SharedCategory']['Members']['Member']
        if not isinstance(members, list):
            members = [members]
        for category in members:
            if int(category['@weight']) > 25:
                categories.append(category)

    if categories:
        category = random.choice(categories)
        descriptors = category['#text'].split(':')
        hint = "".join(["The answer and " + word2 + " are both ", descriptors[0], " ", descriptors[1], "s."])
    else:
        hint = 0
    return hint

def get_dmuse_adjective(word):
    base_url = "https://api.datamuse.com/words?rel_jjb={}&max=1"
    query = base_url.format(word)
    response = requests.get(query)
    data = json.loads(response.content)
    if data:
        hint = "".join(["I could be described as " + data[0]['word'] + "."])
    else:
        hint = 0
    return hint

def get_dmuse_association(word):
    base_url = "https://api.datamuse.com/words?rel_trg={}&max=1"
    query = base_url.format(word)
    response = requests.get(query)
    data = json.loads(response.content)
    if data:
        hint = "".join(["I could be associated with " + data[0]['word'] + "."])
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
    if word2:
        word2vector = frombuffer(word2.vector, float32)
        similarity = round(cosine_similarity(word1vector, word2vector) * 100, 1)
    else:
        similarity = 0;
    return similarity
    

@main.route('/')
def index():
    # If this is the first riddle set up the session data
    if session.get('new_riddle') is None:
        session['new_riddle'] = True
        session['hints'] = []
        session['guesses'] = []
        session['guess_count'] = 0
        session['riddle_completed'] = False
    
    # If a new riddle needs to be generated
    if session['new_riddle']:
        # Get a new word to guess
        session['answer'] = get_new_word()
        
        # Get an initial hint
        list = []
        list.append(get_trex_hint(session['answer']))
        session['hints'] = list
        
        if current_user.is_authenticated:
            current_user.total_hints += 1

        # Clear the guesses and reset completion status
        session['guesses'] = []
        session['guess_count'] = 0
        session['riddle_completed'] = False
    
    return render_template('index.html')

@main.route('/<int:forfeit>', methods=['POST'])
def index_post(forfeit):
    # If it's not a forfeit than it's a guess
    if not forfeit:
        new_guess = request.form['guess'].lower()
        
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
            session['guess_count'] += 1
            
            if current_user.is_authenticated:
                current_user.total_hints += 1
                current_user.total_guesses += 1
            
            # Get similarity between the guess and the answer and add to the list
            similarity = get_similarity(session['answer'], new_guess)
            if not similarity:
                flash('Not a valid word.')
            else:
                list = session['guesses']
                list.append([new_guess, similarity])
                session['guesses'] = list

            # If its the first guess
            if session['guess_count'] == 1:
                hint = get_dmuse_adjective(session['answer'])
                # If hint exists add it to the hint list
                if hint:
                    list = session['hints']
                    list.append(hint)
                    session['hints'] = list

            # If its the second guess
            elif session['guess_count'] == 2:
                hint = get_dmuse_association(session['answer'])
                # If hint exists add it to the hint list
                if hint:
                    list = session['hints']
                    list.append(hint)
                    session['hints'] = list
                
            elif session['guess_count'] > 2 or session['guess_count'] < 5:
                # Get a comparative hint for each guess and if its vaild append it
                comparative_hints = []
                for guess in session['guesses']:
                    comparative_hint = get_comparative_trex_hint(session['answer'], guess[0])
                    if comparative_hint:
                        comparative_hints.append(comparative_hint)
                
                # If there were any valid comparative hints choose a random one and add it to the hint list if its not a repeat
                if comparative_hints:
                    hint = random.choice(comparative_hints)
                    if hint not in session['hints']:
                        list = session['hints']
                        list.append(hint)
                        session['hints'] = list

    # It was a forfeit
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
