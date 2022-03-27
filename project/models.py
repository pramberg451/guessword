from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))
    
    wins = db.Column(db.Integer)
    forfeits = db.Column(db.Integer)
    streak = db.Column(db.Integer)

    total_hints = db.Column(db.Integer)
    total_guesses = db.Column(db.Integer)