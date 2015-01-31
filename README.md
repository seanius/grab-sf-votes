# A Legistar Vote Scraper and More!

This is a collection of little scripts and proof-of-concept frontends that
pull information from different data sources:

 * San Francisco Board of Supervisors' antiquated Legistar website, used to
fill a sqlite database with voting records from BoS meetings.
 * DataSF and the corresponding SODA endpoints, used to fetch JSON blobs
of recorded lobbyist activity (contacts, eventually contributions).

## Setup

You will probably need to run

	pip install -r requirements.txt
	
to satisfy module dependencies. The `reset_db` script also relies on
the sqlite3 command line program, but any sqlite client will do to
fill in the schema.  You'll also need to download some datafiles
for the TextBlob support

	python -m textblob.download_corpora    

## General implementation details

Currently the scripts download data into totally arbitrary local files.  I'm
attempting to maintain a modicum of structure with the code, though:

 * ./cache/: cached copies of dumped html from legistar
 * ./app/\*.html: small often cargo-culted proof-of-concept frontends.
 * ./app/scripts: javascript, borrowed, hacked, maimed, formed.
 * ./app/css, what you'd think.
 * ./data: structured data dumps used by the frontends, the non-legistar
   cached data, basically.

## Running the frontend locally

Since most modern web browsers won't let you fetch json from local files, you
need to serve the content from an actual web server to test it.  If you don't
have one, or are just super lazy, you can use this one-liner to run a simple
static web server:

	python -m SimpleHTTPServer 8080

## The Legistar Scraper

### Usage

Prepare the legistar sqlite database:

    ./reset_db

Dump all the vote data from 2010 to 2014:

    python collect.py 2010 2014

### Practicalities

Basic things are very easy to change. The DB schema is simple, and I wrote
it using an ORM specifically so that you can eaisly change the RDBMS just by
porting the table definitions and editing the connection string in db.py. 
The code is somewhat modular; hopefully the functions will give you an idea
of how things are done. There's a decent amount of boilerplate code for parsing
and paginating Legistar's Telerik grid UI components, which might come in handy
in some other applications. 

### Limitations

The most striking drawback of this approach to data collection is that it
is slow. Because I don't have access to the Granicus Legistar API, I'm going
through their website - an old ASP affair that carries around kilobytes of
VIEWSTATE and sometimes takes 10 seconds to load a page. Unfortunately, in
order to get the data of interest, many page loads are required. Expect to
wait over an hour to get a 3 years of data.

For now, this mostly only supports one-off data collection. You won't get
duplicate fields, but if you've already fetched a particular file/vote
record, you won't see if it's been updated (files are not re-fetched if
they're cached locally).

There are probably other interesting pieces of data buried in the system
that could be extracted. I stuck to what was most clear-cut, to be sure I
could get it right.

### Extensions

There's much more information that could be gleaned from this system.  Various
forms of legislation lifecycle stuff (when was it amended/modified, enacted,
etc), Information on the supervisors themselves, etc.

## Lobbyist Activity

The lobbyist activity scraper fetches reported contacts of city officials
by declared lobbyists.  In some cases this information will be with respect
to specific file numbers (i.e. legislation) from the BoS, which can be
potentially interesting to correlate with the legistar voting records.

To fetch the data, currently just run

	./lobby_record.py

and it should fetch all the requisite data that the frontends will want.
you can optionally pass a start-date to it (default: 1 year ago):

	./lobby_record.py 2014-01-01

and an end date (default: tomorrow):

	./lobby_record.py 2014-01-01 2015-01-01

### Practicalities

This is super simple paginated "fetch *all* the JSON" code.  It can really
easily be re-used to fetch just about any other SODA backed data.  Long
term, unless we need to post-process the data, we don't really need the
code and could fetch the JSON directly, but this makes testing (particularly
offline testing) much easier and removes any worry about over-taxing the
SODA endpoints.

### Limitations

Locally fetching the data means it's not quite live, and we'd need to
have something periodically keeping the data up to date.

### Extensions

There are more data sources in datasf, such as contributions by lobbyists,
contracts received from the city (which could be tied to lobbyist clients,
et c).

## PoC frontends

These are all found in ./app.  Most of them are cargo-culted from examples
in the d3 gallery.  I do my best to credit the sources for the javascript/html.

# Misc TODO items

 * find a straightforward way to host this
 * get more data
 * visualization/frontend work
