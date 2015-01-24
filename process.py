#! /usr/bin/python
import db
import textblob

if __name__ == '__main__':
  counter = 10
  for instance in db.session.query(db.Proposal):
    
    print instance.title
    blob = textblob.TextBlob(instance.title)
    for np in map(unicode, blob.noun_phrases):
      phrase = db.get_or_create(db.session, db.NounPhrase, phrase=np)
      instance.noun_phrases.append(phrase)
    db.session.commit()
    counter -= 1
    if not counter:
      break

  for np in db.session.query(db.NounPhrase):
    print '%s: %s' % (np.phrase, ','.join([str(p.file_number) for p in np.proposals]))

