#! /usr/bin/python

import collections
import datetime
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

def parse_date(date_string):
  """Extract a datetime.date object from a given string."""
  return dateutil.parser.parse(date_string).date()

def timeline_report(_):
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
        ts = time.mktime(parse_date(record['date']).timetuple())
        timeline.add_event(ts, record)

  return [timelines[filenum].json() for filenum in sorted(timelines)] 

def contacts_report(since_when, until_when):
  records = [r for r in sfdata.LobbyistActivity().records()
             if parse_date(r['date']) >= since_when
             and parse_date(r['date']) <= until_when]
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


def department_topics_report(since_when, until_when):
  min_threshold = 4

  records = [r for r in sfdata.LobbyistActivity().records()
             if parse_date(r['date']) >= since_when
             and parse_date(r['date']) <= until_when]
  by_topic = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))

  def clean(str):
    return urllib.quote(str).replace('-', ' ').replace(',', ' ').encode('utf-8')

  for r in records:
    department = clean(r['official_department'])
    topic = clean(r['lobbyingsubjectarea'])
    by_topic[department][topic] += 1

  for department in sorted(by_topic):
    for topic in sorted(by_topic[department]):
      count = by_topic[department][topic]
      key = '-'.join([department, topic])
      if count > min_threshold:
        yield ('%s,%s' % (key, count)).encode('utf-8')


def contact_mapping_report(since_when):
  """Note: Currently unused, may need to re-write."""
  records = [r for r in sfdata.LobbyistActivity().records()
             if parse_date(r['date']) >= since_when]
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

def write_report_as(filename, data):
  tf = tempfile.NamedTemporaryFile(delete=False) 
  tf.write(data)
  tf.close()
  os.rename(tf.name, 'data/%s' % filename)

if __name__ == '__main__':
  default_start = datetime.date.today() - datetime.timedelta(days=365)
  default_end = datetime.date.today() + datetime.timedelta(days=1)
  try:
    since_when = parse_date(sys.argv[1])
  except:
    since_when = default_start
  try:
    until_when = parse_date(sys.argv[2])
  except:
    until_when = default_end

  write_report_as('Timeline.json', json.dumps(timeline_report(since_when)))
  write_report_as(
      'FirmToDeptContacts.csv',
      '\n'.join(contacts_report(since_when, until_when)))

  write_report_as(
      'ByDepartmentByTopic.csv',
      '\n'.join(department_topics_report(since_when, until_when)))

