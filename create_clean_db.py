from project import db, create_app, models
import gensim
from project.models import Word

db.create_all(app=create_app())

app = create_app()

model = gensim.models.KeyedVectors.load("project/word2vec.model")

with app.app_context():
    count = 0
    for word in model.key_to_index:
        if word.isalpha():
            new_word = Word(word=word, vector=model[word])
            db.session.add(new_word)
            
            print(str(count) + " " + str(word))
        count += 1
    db.session.commit()