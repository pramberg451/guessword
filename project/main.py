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
    """Selects a random word from the designated text
    file containing the possible riddle answers"""
    word = random.choice(open("project/nouns.txt").readlines()).strip()
    return word

def get_trex_hint(word):
    """Queries Thesaurus Rex with a single word search.
    Selects a category pair from the data returned and
    constructs a string to return as a hint.
    Returns 0 if no categories were valid"""
    
    # Query Thesarus Rex
    base_url = "http://ngrams.ucd.ie/therex3/common-nouns/member.action?member={term}&kw={term}&needDisamb=false&xml=true"
    query = base_url.format(term=word)
    response = requests.get(query)
    
    # Convert the xml data to json for easy parsing
    json_string = json.dumps(xmltodict.parse(response.content))
    data = json.loads(json_string)
    
    # Create a list of category pairs from the data so we can choose a random one
    # The category must have a weight of > 25 to be valid.
    categories = []
    if len(data['MemberData']['Categories']) > 1:
        for category in data['MemberData']['Categories']['Category']:
            if int(category['@weight']) > 25:
                categories.append(category)
    
    # If there were categories added to the list, choose a random one construct
    # a hint from it and return it, otherwise return 0
    if categories:
        category = random.choice(categories)
        descriptors = category['#text'].split(':')
        hint = "".join(["I am a ", descriptors[0], " ", descriptors[1], "."])
    else:
        hint = 0
    return hint

def get_comparative_trex_hint(word1, word2):
    """Queries Thesaurus Rex with a double word search
    for a comparison. Selects a category pair from the 
    data returned and constructs a string to return as 
    a hint. Returns 0 if no categories were valid"""
    
    # Query Thesarus Rex
    base_url = "http://ngrams.ucd.ie/therex3/common-nouns/share.action?word1={word1}&word2={word2}&xml=true"
    query = base_url.format(word1 = word1, word2 = word2)
    response = requests.get(query)
    
    # Convert the xml data to json for easy parsing
    json_string = json.dumps(xmltodict.parse(response.content))
    data = json.loads(json_string)
    
    # Create a list of category pairs from the data so we can choose a random one
    # The category must have a weight of > 25 to be valid.
    categories = []
    # If the data returned contains categories
    if len(data['SharedCategory']['Members']) > 2:
        members = data['SharedCategory']['Members']['Member']
        # There is an isntance where if the data only has one category its not returned
        # in a list so we need to place it into a list if thats the case
        if not isinstance(members, list):
            members = [members]
        for category in members:
            if int(category['@weight']) > 25:
                categories.append(category)
    
    # If there were categories added to the list, choose a random one construct
    # a hint from it and return it, otherwise return 0
    if categories:
        category = random.choice(categories)
        descriptors = category['#text'].split(':')
        hint = "".join(["The answer and " + word2 + " are both ", descriptors[0], " ", descriptors[1], "s."])
    else:
        hint = 0
    return hint

def get_dmuse_adjective(word):
    """Queries the Datamuse API in order to get an
    adjective for the supplied word. Returns a 
    string of a hint constructed using that adjective."""
    
    # Query Datamuse
    base_url = "https://api.datamuse.com/words?rel_jjb={}&max=1"
    query = base_url.format(word)
    response = requests.get(query)
    data = json.loads(response.content)
    
    # Construct and return a hint using the first given adjective.
    # If no adjectives were available, return 0.
    if data:
        hint = "".join(["I could be described as " + data[0]['word'] + "."])
    else:
        hint = 0
    return hint

def get_dmuse_association(word):
    """Queries the Datamuse API in order to get an
    association for the supplied word. Returns a 
    string of a hint constructed using that association."""
    
    # Query Datamuse
    base_url = "https://api.datamuse.com/words?rel_trg={}&max=1"
    query = base_url.format(word)
    response = requests.get(query)
    data = json.loads(response.content)
    
    # Construct and return a hint using the first given association.
    # If no associations were available, return 0.
    if data:
        hint = "".join(["I could be associated with " + data[0]['word'] + "."])
    else:
        hint = 0
    return hint

def cosine_similarity(word1, word2):
    """Calculates the cosine similarity between given two word vectors"""
    
    # The sum of corresponding elements in the lists multiplied together
    top = sum(a * b for a, b in zip(word1, word2))
    
    # The sqrt of each element in the list squared added together
    sqrt_word1 = round(sqrt(sum([a * a for a in word1])), 3)
    sqrt_word2 = round(sqrt(sum([b * b for b in word2])), 3)
    bottom = sqrt_word1 * sqrt_word2
    
    return round(top / float(bottom),3)

def get_similarity(answer, guess):
    """Gets two word vectors from the database and returns
    the similarity between the two words as a percentage. The
    second word is check because it was a guess and it's
    possible that the guess is not in the database."""
    
    # Get both the answer and the guesses corresponding vectors from the database
    word1 = Word.query.filter_by(word=answer).first()
    word1vector = frombuffer(word1.vector, float32)
    word2 = Word.query.filter_by(word=guess).first()
    
    # If the guess was valid and had a corresponding vector, calculate
    # the similarity and return it
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
        # Clear the guesses and reset completion status
        session['guesses'] = []
        session['guess_count'] = 0
        session['riddle_completed'] = False
        
        # Get a new word to guess
        session['answer'] = get_new_word()
        
        # Get an initial hint
        list = []
        list.append(get_trex_hint(session['answer']))
        session['hints'] = list
        
        # If a user is logged in track the hint
        if current_user.is_authenticated:
            current_user.total_hints += 1
    
    return render_template('index.html')

@main.route('/<int:forfeit>', methods=['POST'])
def index_post(forfeit):
    # If it's not a forfeit than it's a guess
    if not forfeit:
        # Get the guess from the form
        new_guess = request.form['guess'].lower()
        
        # If guess was correct flash a message and update stats
        if new_guess == session['answer']:
            flash(session['answer'] + ' was correct!')
            session['riddle_completed'] = True
            
            if current_user.is_authenticated:
                current_user.wins += 1
                current_user.streak += 1
        
        # If guess was a repeat flash a message
        elif any(new_guess in guess for guess in session['guesses']):
            flash('That has already been guessed.')
    
        # If guess was incorrect, continue game and provide another hint
        else:
            # If as user is logged in track the guess and the new hint
            if current_user.is_authenticated:
                current_user.total_hints += 1
                current_user.total_guesses += 1
            
            # Update the guess count in order to get the correct kind of hint
            # for the number of guesses the player has made
            session['guess_count'] += 1
            
            # Get similarity between the guess and the answer and add to the guess list
            similarity = get_similarity(session['answer'], new_guess)
            # If no similarity is returned that means the guess was not found in the database
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
            
            # If its the third or fourth guess
            elif session['guess_count'] > 2 or session['guess_count'] < 5:
                # Get a comparative hint for each guess and if its vaild add it to a list
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
        # Flash what the answer was and complete the riddle
        flash('The answer was ' + session['answer'] + ".")
        session['riddle_completed'] = True
        
        # If a user is logged in, track the forfeit and reset their streak
        if current_user.is_authenticated:
            current_user.forfeits += 1
            current_user.streak = 0
    
    db.session.commit()
    return render_template('index.html')

@main.route('/stats')
@login_required
def stats():
    return render_template('stats.html', username=current_user.username)
