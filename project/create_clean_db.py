from project import db, create_app, models
import gensim
from project.models import Word

db.create_all(app=create_app())

model = gensim.models.KeyedVectors.load("project/word2vec.model")

new_word = Word(word='carrot', vector=model['carrot'])
db.session.add(new_word)
db.session.commit()