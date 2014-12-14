A Legistar Vote Scraper
=======================

This is a little script that pulls information about past votes from the San 
Francisco Board of Supervisors' antiquated Legistar website and uses it to
fill a sqlite database.  'antiquated' is a euphemism, really.  It's a horrible
beast of an application.

Usage
-----
Prepare the database:

    ./reset_db

Dump all the vote data from 2010 to 2014:

    python collect.py 2010 2014

Setup
-----
You will probably need to run

	pip install -r requirements.txt
	
to satisfy module dependencies. The reset_db script also relies on
the sqlite3 command line program, but any sqlite client will do to
fill in the schema.  You'll also need to download some datafiles
for the TextBlob support

	python -m textblob.download_corpora    

Practicalities
--------------
Basic things are very easy to change. The DB schema is simple, and I wrote
it using an ORM specifically so that you can eaisly change the RDBMS just by
porting the table definitions and editing the connection string in db.py. 
The code is somewhat modular; hopefully the functions will give you an idea
of how things are done. There's a decent amount of boilerplate code for parsing
and paginating Legistar's Telerik grid UI components, which might come in handy
in some other applications. 

Limitations
-----------
The most striking drawback of this approach to data collection is that it
is slow. Because I don't have access to the Granicus Legistar API, I'm going
through their website - an old ASP affair that carries around kilobytes of
VIEWSTATE and sometimes takes 10 seconds to load a page. Unfortunately, in
order to get the data of interest, many page loads are required. Expect to
wait over an hour to get a 3 years of data.

For now, this only supports one-off data collection. You will get duplicate
records for vote events and votes cast if you run it a second time with any
overlapping range. The main challenge is adding more fields to uniquely 
identify vote events.

There are probably other interesting pieces of data buried in the system
that could be extracted. I stuck to what was most clear-cut, to be sure I
could get it right.

Extensions
----------
1. Profile the code and speed things up where possible
2. There is an Excel (xls) export on the Legistar site. See if there is a 
   way to leverage that while not losing the ability to grab details about
   legislation.
3. Get some more info about the supervisors into the DB - supervisors are
   people (TM), too!
