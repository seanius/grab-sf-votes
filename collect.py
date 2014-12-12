#! /usr/bin/python
"""
A python script to scrape voting records etc from the SF BoS legistar
system.
    - Sean Finney (seanius@gmail.com)

Derived from:

A webdriver/selenium based scraper for San Francisco Board of Supervisors
voting data.
    - Troy Deck (troy.deque@gmail.com)
"""
import db

import argparse
import bs4
import datetime
import json
import logging
import os
import re
import requests
import tempfile
import time

#############
# Constants #
#############
# website root
BASE_SITE = 'https://sfgov.legistar.com'
# first page to visit, to initialize the form and server-side state.
VOTE_LISTING_FIRST_URL = 'https://sfgov.legistar.com/MainBody.aspx'
# subsequent requesets to update the form UI and scrape the votes go here.
VOTE_PAGING_FORM_URL = 'https://sfgov.legistar.com/DepartmentDetail.aspx?ID=7374&GUID=978C35A3-7173-49E6-8FAA-8EA34A7D4160&Mode=MainBody'

# id of the element containing the voting table and navigation controls.
VOTING_GRID_ID = 'ctl00_ContentPlaceHolder1_gridVoting_ctl00'
# drop-down voting-year-selector
YEAR_SELECTOR_ID = 'ctl00_ContentPlaceHolder1_lstTimePeriodVoting_DropDown'

class LegistarNavigator(object):
  """"Helper class to fetch/post data to legistar."""
  def __init__(self):
    # TODO: not a good location
    self._cache_dir = './cache'
    self.cookie = {}
    self._asp_attrs = {}

  def fetch(self, url, name, payload=None):
    """GET/POST a URL into a local cache file.

    Args:
      url, string, the fully qualified URL.
      name, string, unique name for file in cache dir.
      payload, dict, if nonempty, k/v pairs to POST to URL.

    this class also stashes a cookie between requests which can be
    used to control sorting order etc.
    
    Returns:
      bs4.BeautifulSoup of the fetched page.
    """
    cache_file = '%s/%s.html' % (self._cache_dir, name)
    logging.info("%s -> %s" % (url, cache_file))
    if not os.path.exists(cache_file):
      tmp_file = tempfile.NamedTemporaryFile(delete=False)
      if not payload:
        response = requests.get(url, cookies=self.cookie)
      else:
        payload.update(self._asp_attrs)
        response = requests.post(url, data=payload, cookies=self.cookie)
      self.cookie = response.cookies
      tmp_file.write(response.content)
      os.rename(tmp_file.name, cache_file)

    soup = bs4.BeautifulSoup(file(cache_file))
    asp_attrs = ['__VIEWSTATE', '__EVENTVALIDATION', '__VIEWSTATEGENERATOR']
    for asp_attr in asp_attrs:
      attr_element = soup.find(id=asp_attr)
      if attr_element and attr_element['value']:
        self._asp_attrs[asp_attr] = attr_element['value']

    return soup


class VotingInterfaceInfo(object):
  """An awkward but whatever helper class for parsing state of the form.
  
  after initializing with a bs4.BeautifulSoup instance from a scraped
  voting page, this class should have some helpful pre-parsed attributes
  for determining the state of the form, for manipulating it further.
  namely:
  
    current_page, string, the current page number (for paginated results).
    next_page, string, the next page number (for paginated results).  May also
      be '...', in the case that there are more than 14 pages with results.
    next_page_target, string, an arbitrary string in the page which needs to
      be passed as the __EVENTTARGET in the POST, when paginating to the
      next page number.
    next_page_arg, string, same, but for __EVENTARGUMENT.
    year_dropdown_indicies, dict, string -> int mappings where the key
      is a year found in the "select voting period" dropdown filter, and the
      value is the index in the dropdown field, which is needed in the
      POST request.
  """


  def __init__(self, soup):
    self.current_page = None
    self.next_page = None
    self.next_page_target = None
    self.next_page_arg = None
    self.year_dropdown_indices = {}

    # parse the year dropdown
    dropdown = soup.find(id=YEAR_SELECTOR_ID)
    list_items = dropdown.select('div > ul > li')
    for (num, li) in enumerate(list_items, 1):
      self.year_dropdown_indices[li.text] = num

    # find the paginated results heading for the vote table
    table = soup.find(id=VOTING_GRID_ID)
    page_elements = table.select('thead > tr.rgPager > td > table > tbody > tr > td > div > a.rgCurrentPage')

    if len(page_elements):
      page_element = page_elements[0]
      self.current_page = page_element.span.text
      next_page_element = page_element.next_sibling
      try:
        next_page = next_page_element.span.text

        if next_page == '...':
          next_page = str(int(self.current_page) + 1)

        # the "page N" links are actually javascript callouts to this
        # "doPostBack" function.  the arguments to doPostBack are the
        # __EVENTTARGET and __EVENTARGUMENT fields in the resulting POST.
        href = next_page_element['href']
        match = re.match(".*doPostBack\('([^']*)','([^']*)'\)", href)

        self.next_page = next_page
        self.next_page_target = match.group(1)
        self.next_page_arg = match.group(2)
      finally:
        return


#
# Main scraping functions
#
def scrape_proposal_page(proposal_url, file_number):
    """
    Navigates to the page giving details about a piece of legislation, scrapes
    that data, and adds a model to the database session. Returns the new DB
    model.
    """
    fetcher = LegistarNavigator()
    soup = fetcher.fetch(
        '%s/%s' % (BASE_SITE, proposal_url),
        'file-%s' % (file_number))
    try:
      file_number = int(extract_text(soup.find(
        id='ctl00_ContentPlaceHolder1_lblFile2')))
      proposal_title = extract_text(soup.find(
        id='ctl00_ContentPlaceHolder1_lblTitle2'))
      proposal_type = extract_text(soup.find(
        id='ctl00_ContentPlaceHolder1_lblIntroduced2'))
      proposal_status = extract_text(soup.find(
        id='ctl00_ContentPlaceHolder1_lblStatus2'))
      introduction_date = parse_date(extract_text(soup.find(
        id='ctl00_ContentPlaceHolder1_lblIntroduced2')))
    except:
      logging.warn('Unable to scrape proposal %s' % (file_number))
      return
    
    db_proposal = db.Proposal(file_number, proposal_title)
    db_proposal.status = proposal_status
    db_proposal.proposal_type = proposal_type
    db_proposal.introduction_date = introduction_date
    
    db.session.add(db_proposal) 
    db.session.commit()
    return db_proposal


def scrape_vote_page(soup):
    """
    Assuming the browser is on a page containing a grid of votes, scrapes
    the vote data to populate the database.
    """
    # Get the contents of the table
    headers, rows = extract_grid_cells(soup, VOTING_GRID_ID)
    # Do a quick check to ensure our assumption about the headers is correct
    assert headers[:6] == [
        u'File #', 
        u'Action Date', 
        u'Title', 
        u'Action Details', 
        u'Meeting Details',
        u'Tally',
    ]

    # Go through the supervisors and add them to the DB if they are missing
    supervisors = headers[6:]
    legislator_objects = {}

    # Pull values from each row and use them to populate the database
    try:
        for row in rows: 
            file_number = int(extract_text(row['File #']))
            action_date = parse_date(extract_text(row['Action Date']))

            # Find the proposal in the DB, or, if it isn't there,
            # create a record for it by scraping the info page about that 
            # proposal.
            db_proposal = find_proposal(file_number) or (
                scrape_proposal_page(row['File #'].a['href'], file_number))
            if not db_proposal:
              continue

            db_vote_event = db.VoteEvent(db_proposal, action_date)
            db.session.add(db_vote_event)
            db.session.flush()
            db.session.commit()

            for name in supervisors:
                vote_cast = extract_text(row[name])
                if vote_cast in ('Aye', 'No'):
                    db.session.add(db.Vote(
                        record_supervisor(name),
                        db_proposal,
                        vote_cast == 'Aye'
                    ))
    finally:
      db.session.flush()
      db.session.commit()


def scrape_vote_years(year_range):
  """
  Opens the votes page and scrapes the votes for all years in the given range.
  Populates the database and commits the transaction
  """
  for year in year_range:
    try:
      # OK, so first we go to the frontpage and navigate our way to the
      # voting results (this is necessary to get the wonderful snowflake
      # of an app that legistar is to register some necessary server-side state.
      fetcher = LegistarNavigator()
      fetcher.fetch(VOTE_LISTING_FIRST_URL, 'frontpage')

      # From the front page, we click the "Votes" tab, which translates to
      # a POST request to the server.
      payload = json.load(file('payload-select-votes.json'))
      payload['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$tabTop'
      payload['__EVENTARGUMENT'] = '{"type":0,"index":"2"}'
      soup = fetcher.fetch(VOTE_PAGING_FORM_URL, 'votes-selected',
                           payload=payload)
      pager_info = VotingInterfaceInfo(soup)

      # Now we select a given year from a dropdown widget, which again
      # translates to a POST request to the server.
      payload = json.load(file('payload-year-select.json'))
      payload['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$lstTimePeriodVoting'
      payload['__EVENTARGUMENT'] = '{"Command":"Select","Index":%s}' % (
          pager_info.year_dropdown_indices[str(year)])
      payload['ctl00$ContentPlaceHolder1$lstTimePeriodVoting'] = str(year)
      payload['ctl00_ContentPlaceHolder1_lstTimePeriodVoting_ClientState'] = "{\"logEntries\":[],\"value\":\"%s\",\"text\":\"%s\",\"enabled\":true,\"checkedIndices\":[],\"checkedItemsTextOverflows\":false}" % (year, year)

      # This gives some results, which may be paginated.
      soup = fetcher.fetch(
          VOTE_PAGING_FORM_URL, 
          'vote-listings-%s-page-1' % (year,),
          payload=payload)
      scrape_vote_page(soup)

      while True:
        # repeat the process for every page in the paginated results.
        pager_info = VotingInterfaceInfo(soup)
        if pager_info.next_page == None:
          break
        payload = json.load(file('payload-page-select.json'))
        payload['__EVENTTARGET'] = pager_info.next_page_target
        payload['__EVENTARGUMENT'] = pager_info.next_page_arg
        soup = fetcher.fetch(
            VOTE_PAGING_FORM_URL,
            'vote-listings-%s-page-%s' % (year, pager_info.next_page),
            payload=payload)
        scrape_vote_page(soup)

    except:
      db.session.rollback()
      raise

#
# Browser/DOM helpers
#

def extract_grid_cells(soup, grid_id):
    """
    Given the ID of a legistar table, returns a list of dictionaries
    for each row mapping column headers to td elements.
    """
    table = soup.find(id=grid_id)
    
    header_cells = table.find_all(class_='rgHeader')
    headers = [extract_text(cell) for cell in header_cells]

    rows = table.find_all(class_='rgRow')

    result_rows = []
    for row in rows:
        cells = {}
        td_elements = row.find_all('td')
        for header, cell in zip(headers, td_elements):
            cells[header] = cell

        result_rows.append(cells)

    return (headers, result_rows)

def extract_text(element):
    """
    Returns the text from an element in a nice, readable form with whitespace 
    trimmed and non-breaking spaces turned into regular spaces.
    """
    return element.get_text().replace(u'\xa0', ' ').strip()

def parse_date(date_text):
    """
    Converts a date string in the American mm/dd/yyyy format to a Python
    date object.
    """
    month, day, year = [int(field) for field in date_text.split('/')]
    return datetime.date(year, month, day)

#
# DB helpers
#
def record_supervisor(name):
    """ 
    Queries for the given supervisor, creates a record for them in the 
    database if they aren't there already, and returns a Legislator
    object.
    """
    legislator = db.session.query(db.Legislator).filter_by(name=name).first()
    if not legislator:
        legislator = db.Legislator(name)
        db.session.add(legislator)
        db.session.flush()

    return legislator

def find_proposal(file_number):
    """
    Queries the database for a proposal based on its file number. Returns
    either the proposal model or None if it is not recorded.
    """
    return (db.session.query(db.Proposal)
        .filter_by(file_number=file_number)
        .first()
    )

##
## Main script
##
if __name__ == '__main__':
  logging.basicConfig(level='INFO')
  parser = argparse.ArgumentParser(description=
      '''
      Populate a database with several years of voting records from the San 
      Francisco board of supervisors.
      '''
  )
  parser.add_argument('first_year', metavar='first year', type=int)
  parser.add_argument('last_year', metavar='last year', type=int)
  args = parser.parse_args()
  scrape_vote_years(range(args.first_year, args.last_year + 1))
