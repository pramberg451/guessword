from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    """A class to represent a user in the database with
    as username, password and stats that are tracked by
    the game."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))
    
    wins = db.Column(db.Integer)
    forfeits = db.Column(db.Integer)
    streak = db.Column(db.Integer)

    total_hints = db.Column(db.Integer)
    total_guesses = db.Column(db.Integer)

class Word(db.Model):
    """A class to represent a word and it's corresponding
    vector in the database. The vector is stored as large 
    binary"""
    word = db.Column(db.String(50), primary_key=True)
    vector = db.Column(db.BLOB)