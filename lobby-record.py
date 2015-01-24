#! /usr/bin/python

import collections
import dateutil.parser
import json
import os
import sys
import urllib
import tempfile
import time

import collect
import sfdata

class Timeline(object):

  def __init__(self, title):
    self._title = title
    self._events = []

  def add_event(self, date, event):
    self._events.append((date,event))

  def json(self):
    d = {'title': self._title, 'events': list()}
    for event in sorted(self._events, lambda x, y: cmp(x[0], y[0])):
      d['events'].append(event)
    return d

def file_numbers(record):
  numbers = []
  filenumber = record.get('filenumber', '')
  for s in filenumber.split():
    try:
      i = int(s)
      numbers.append(i)
    except:
      pass
  return numbers

def iso_datetime(date_string):
  return dateutil.parser.parse(date_string)

def timeline_report():
  timelines = {}
  for record in sfdata.LobbyistActivity().records():
    for file_number in file_numbers(record):
      proposal = collect.find_proposal(file_number)
      if proposal:
        if file_number not in timelines:
          timeline = Timeline(proposal.title)
          introduction_ts =  time.mktime(proposal.introduction_date.timetuple())
          timeline.add_event(introduction_ts, 'introduced')
          timelines[file_number] = timeline
        else:
          timeline = timelines[file_number]
        ts = time.mktime(iso_datetime(record['date']).timetuple())
        timeline.add_event(ts, record)

  return [timelines[filenum].json() for filenum in sorted(timelines)] 

def contacts_report(since_when):
  records = [r for r in sfdata.LobbyistActivity().records()
             if iso_datetime(r['date']) >= since_when]
  contacts = collections.defaultdict(
      lambda: collections.defaultdict(
          lambda: collections.defaultdict(
              lambda: collections.defaultdict(lambda: 0))))
  for r in records:
    contacts[r['official_department']][r['official']][r['lobbyist_firm']][r['lobbyist_client']] += 1

  for department in sorted(contacts):
    for official in sorted(contacts[department]):
      for firm in sorted(contacts[department][official]):
        for client in sorted(contacts[department][official][firm]):
          count = contacts[department][official][firm][client]
          key = '-'.join([department, official, firm, client]).encode('utf-8')
          yield ('%s,%s' % (urllib.quote(key), count)).encode('utf-8')


def contact_mapping_report(since_when):
  records = [r for r in sfdata.LobbyistActivity().records()
             if iso_datetime(r['date']) >= since_when]
  officials = set([r['official_department'] for r in records])
  clients = set([r['lobbyist_firm'] for r in records])
  matrix_positions = {}
  reverse_mappings = []
  for (pos, person) in enumerate(clients.union(officials)):
    matrix_positions[person] = pos
    reverse_mappings.append(person)

  matrix = [[0] * len(matrix_positions)] * len(matrix_positions)
    
  for record in records:
    client_pos = matrix_positions[record['lobbyist_firm']]
    official_pos = matrix_positions[record['official_department']]
    matrix[client_pos][official_pos] += 1

  return {'mappings': reverse_mappings, 'matrix': matrix}

if __name__ == '__main__':
  since_when = iso_datetime(sys.argv[1])

  tf = tempfile.NamedTemporaryFile(delete=False) 
  tf.write(json.dumps(timeline_report()))
  tf.close()
  os.rename(tf.name, 'Timeline.json')

  tf = tempfile.NamedTemporaryFile(delete=False) 
  tf.write('\n'.join(contacts_report(since_when)))
  tf.close()
  os.rename(tf.name, 'FirmToDeptContacts.csv')



