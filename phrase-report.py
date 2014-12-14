#! /usr/bin/python
#
# a short and simple script to print out a histogram of the phrase
# groupings found in the database.
#
import db
import collections

if __name__ == '__main__':
  phrase_histo = collections.defaultdict(list)
  for np in db.session.query(db.NounPhrase):
    file_ids = [unicode(p.file_number) for p in np.proposals]
    phrase_histo[len(file_ids)].append((np.phrase, file_ids))

  for count in sorted(phrase_histo):
    for phrase, ids in phrase_histo[count]:
      print '(%s) %s: %s' % (count, phrase, ', '.join(ids))

