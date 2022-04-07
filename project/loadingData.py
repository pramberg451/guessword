from math import sqrt
import gensim
from .models import Word
from . import db

def square_rooted(x):
    return round(sqrt(sum([a*a for a in x])),3)

def cosine_similarity(x,y):
    numerator = sum(a*b for a,b in zip(x,y))
    denominator = square_rooted(x)*square_rooted(y)
    return round(numerator/float(denominator),3)


model = gensim.models.KeyedVectors.load("project/word2vec.model")

new_word = Word(word='carrot', vector=model['carrot'])
db.session.add()
