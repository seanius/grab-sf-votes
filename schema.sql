CREATE TABLE legislators (
	id INTEGER NOT NULL, 
	name VARCHAR(255), 
	PRIMARY KEY (id)
);
CREATE TABLE proposals (
	id INTEGER NOT NULL, 
	title VARCHAR, 
	file_number INTEGER, 
	status VARCHAR(255), 
	introduction_date DATE, 
	proposal_type VARCHAR(255), 
	PRIMARY KEY (id)
);
CREATE TABLE noun_phrases (
	id INTEGER NOT NULL, 
	phrase VARCHAR, 
	PRIMARY KEY (id)
);
CREATE TABLE vote_events (
	id INTEGER NOT NULL, 
	vote_date DATE, 
	proposal_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(proposal_id) REFERENCES proposals (id)
);
CREATE TABLE proposals_and_phrases (
	proposal_id INTEGER NOT NULL, 
	noun_phrase_id INTEGER NOT NULL, 
	PRIMARY KEY (proposal_id, noun_phrase_id), 
	FOREIGN KEY(proposal_id) REFERENCES proposals (id), 
	FOREIGN KEY(noun_phrase_id) REFERENCES noun_phrases (id)
);
CREATE TABLE votes (
	legislator_id INTEGER NOT NULL, 
	vote_event_id INTEGER, 
	aye_vote BOOLEAN, 
	PRIMARY KEY (legislator_id, vote_event_id), 
	FOREIGN KEY(legislator_id) REFERENCES legislators (id), 
	FOREIGN KEY(vote_event_id) REFERENCES vote_events (id), 
	CHECK (aye_vote IN (0, 1))
);
