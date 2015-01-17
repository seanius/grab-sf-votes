#! /usr/bin/python

import collections
import datetime
import json
import logging
import networkx
import networkx.readwrite.json_graph.node_link as networkx_json
import os
import requests
import tempfile

class SodaEndPoint(object):
  @property
  def url(self):
    raise NotImplemented("Must define this in subclass")

  @property
  def name(self):
    return self.__class__.__name__

  @property
  def field_maps(self):
    raise NotImplemented("Must define this in subclass")

  @property
  def cache_file(self):
    return "%s.json" % (self.name)

  limit = 50000
  order = ':id'

  def __init__(self):
    self._fetched = False

  def fetch(self):
    result = []
    if not os.path.exists(self.cache_file):
      offset = 0
      while True:
        logging.info('fetching records %d - %d' % (offset, offset + self.limit - 1))
        url = '%s?$order=%s&$offset=%d&$limit=%d' % (self.url, self.order, offset, self.limit)
        resp = requests.get(url)
        logging.info('%s => %s' % (url, resp.status_code))
        resp.raise_for_status()
        data = resp.json()
        if data:
          result.extend(resp.json())
          offset += self.limit
        else:
          break
      tmp_file = tempfile.NamedTemporaryFile(delete=False)
      tmp_file.write(json.dumps(result, indent=1))
      os.rename(tmp_file.name, self.cache_file)
    self._fetched = True

  def records(self):
    if not self._fetched:
      self.fetch()
    return json.load(file(self.cache_file))
    
     
class LobbyistActivity(SodaEndPoint):
  url = 'https://data.sfgov.org/resource/hr5m-xnxc.json'


if __name__ == '__main__':
  LobbyistActivity().fetch()
