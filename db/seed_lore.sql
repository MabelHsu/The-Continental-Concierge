-- ============================================================================
-- SEED DATA — The Continental, New York
-- ============================================================================

INSERT INTO story_state (current_day, current_phase, crisis_level, crisis_name, hotel_status)
VALUES (1, 'evening', 3, 'The Succession Question', 'open');

-- ============================================================================
-- HOTEL RULES
-- ============================================================================
INSERT INTO hotel_rules (rule_number, title, description, penalty, exceptions) VALUES
(1, 'No Business on Continental Grounds',
 'No assassinations, no contracts executed, no violence of any kind may be conducted on the premises of The Continental Hotel.',
 'Excommunicado status. All services revoked. Open contract issued.',
 'Self-defense in extremis, as judged by management.'),
(2, 'All Markers Must Be Honored',
 'A blood marker, once given, represents an unbreakable oath. The bearer may call upon it at any time, and the debtor must comply.',
 'Excommunicado status. The debt doubles and transfers to the next of kin.', NULL),
(3, 'The Continental Is Neutral Ground',
 'No faction, family, or table member may claim jurisdiction within these walls. All guests are equal under the roof.',
 'Faction privileges suspended. Management reserves the right to revoke membership.',
 'During declared states of emergency by the High Table.'),
(4, 'Management Decisions Are Final',
 'The Concierge and Manager speak with the authority of the institution. Their rulings on etiquette, room assignments, and disputes are binding.',
 'Ejection from the premises. Temporary ban of no less than 30 days.', NULL),
(5, 'Guests Must Register Upon Arrival',
 'All guests must present themselves at the front desk and declare their identity and purpose. Aliases are acceptable if registered.',
 'Denial of services. Suspicious unregistered guests may be reported.',
 'Members of the High Table may register through proxies.'),
(6, 'Debts Incurred on Premises Are Binding',
 'Any wager, deal, or agreement made within Continental walls is witnessed by the house and is enforceable.',
 'The house may garnish services, revoke room access, or impose surcharges.', NULL),
(7, 'No Weapons in Common Areas',
 'Firearms and bladed weapons longer than four inches must be checked at the armory before entering dining rooms, bars, or lounges.',
 'Confiscation. First offense: warning. Second offense: 48-hour service suspension.',
 'Concealed weapons under six inches are tolerated in private rooms and hallways.'),
(8, 'The Sommelier Must Be Consulted for Acquisitions',
 'All specialty equipment, munitions, and tactical provisions must go through the Continental''s designated Sommelier.',
 'Unauthorized procurement results in a 200% surcharge and a formal reprimand.', NULL),
(9, 'Guest Privacy Is Sacrosanct',
 'No guest''s room number, personal schedule, or private affairs may be disclosed to another guest without explicit consent.',
 'Staff termination. For guests who violate: one formal warning, then ejection.',
 'Management may override in cases of imminent threat to the hotel.'),
(10, 'The Doctor Is Always In',
 'Medical services are available to all guests at all hours. The doctor asks no questions about the nature of injuries.',
 'N/A — this is a guarantee, not a restriction.', NULL);

-- ============================================================================
-- FACTIONS
-- ============================================================================
INSERT INTO factions (name, type, influence, territory, status, description) VALUES
('The High Table', 'high_table', 95, 'Global', 'active',
 'The supreme governing body of the underworld. Twelve seats, each representing a different sphere of criminal enterprise.'),
('The Continental', 'continental', 80, 'The Continental Hotel, NYC', 'active',
 'The hotel itself as an institution. Neutral ground. Its authority derives from the High Table but operates with significant autonomy.'),
('The Ruska Roma', 'family', 60, 'Brighton Beach, Brooklyn', 'active',
 'A Belarusian crime family with deep roots in the old world. They value loyalty above all and have a long memory for slights.'),
('The Camorra', 'syndicate', 70, 'Little Italy, Lower Manhattan', 'active',
 'Italian crime syndicate. Seat at the High Table. Old money, old grudges, very particular about protocol.'),
('The Bowery King''s Network', 'guild', 45, 'Underground NYC', 'active',
 'A network of informants, outcasts, and the dispossessed. They see everything from below. Not recognized by the High Table.'),
('The Osaka Continental', 'continental', 65, 'Osaka, Japan', 'active',
 'Sister Continental. Their manager has been sending envoys recently. Unknown agenda.'),
('The Adjudicator''s Office', 'high_table', 85, 'Mobile', 'active',
 'Enforcement arm of the High Table. When they arrive, someone is about to have a very bad day.');

-- ============================================================================
-- LOCATIONS
-- ============================================================================
INSERT INTO locations (name, type, district, is_continental, is_neutral, capacity, current_status, description) VALUES
('The Front Desk', 'hotel_service', 'Lobby', true, true, 5, 'accessible',
 'The nerve center. Marble counters, brass bells, leather-bound ledgers. This is where you work.'),
('The Lounge', 'hotel_common', 'Ground Floor', true, true, 40, 'accessible',
 'Low lighting, jazz piano, top-shelf everything. Where deals are whispered and alliances are tested.'),
('The Continental Bar', 'hotel_common', 'Ground Floor', true, true, 25, 'accessible',
 'The bar where everyone pretends they are not watching everyone else.'),
('The Dining Room', 'hotel_common', 'Ground Floor', true, true, 60, 'accessible',
 'White tablecloths, silver service, and conversations that could end empires.'),
('The Armory', 'hotel_service', 'Basement Level 1', true, true, 3, 'accessible',
 'The Sommelier''s domain. If it fires, cuts, or explodes, he has it—or can get it.'),
('The Doctor''s Suite', 'hotel_service', 'Basement Level 2', true, true, 8, 'accessible',
 'Sterile, efficient, discreet. The doctor has seen everything and says nothing.'),
('Room 818', 'hotel_room', 'Floor 8', true, true, 2, 'accessible',
 'Corner suite. Currently occupied by Sofia Al-Azwar. Excellent sight lines.'),
('Room 1201', 'hotel_room', 'Floor 12', true, true, 2, 'restricted',
 'The penthouse suite. Reserved for High Table representatives.'),
('The Roof Garden', 'hotel_common', 'Rooftop', true, true, 20, 'accessible',
 'Open air. City views. Where people go to think, or to be seen thinking.'),
('The Service Tunnels', 'hotel_service', 'Sub-Basement', true, false, NULL, 'accessible',
 'Staff only. Connects to the old subway. Management pretends these don''t exist.'),
('Central Park South', 'street', 'Midtown', false, false, NULL, 'accessible',
 'The buffer zone between the hotel and the real world.'),
('The Bowery', 'territory', 'Lower Manhattan', false, false, NULL, 'accessible',
 'The Bowery King''s domain. Every pigeon, every panhandler, every shadow—his eyes.'),
('Little Italy Social Club', 'safehouse', 'Little Italy', false, false, 15, 'accessible',
 'Camorra territory. Espresso, cannoli, and quiet conversations about loud problems.'),
('Brighton Beach Bathhouse', 'safehouse', 'Brooklyn', false, false, 30, 'accessible',
 'Ruska Roma meeting ground. Steam, vodka, and old world negotiations.'),
('Grand Central Terminal', 'transit', 'Midtown', false, true, NULL, 'accessible',
 'The crossroads. Neutral by default, contested by ambition.');

-- ============================================================================
-- CHARACTERS
-- ============================================================================
INSERT INTO characters (name, alias, title, faction_id, status, reputation, traits, backstory, current_location_id, notes) VALUES
('Winston', NULL, 'Manager of The Continental', 2, 'active', 88,
 '["diplomatic","calculating","principled","dangerous_when_cornered"]',
 'Has managed The Continental for decades. Survived three attempted coups, two High Table audits, and one very personal betrayal. His loyalty is to the institution, not to any person.',
 NULL, 'Your boss. Trusts your judgment but watches everything.'),
('Charon', NULL, 'Former Head Concierge', 2, 'active', 92,
 '["unflappable","precise","loyal","mysterious_past"]',
 'The concierge who came before you. Now semi-retired but still around. Knows every secret this hotel has ever kept.',
 3, 'Available for consultation. Prefers the bar after 9 PM.'),
('Sofia Al-Azwar', 'The Director', 'Manager, Casablanca Continental', NULL, 'active', 75,
 '["fierce","independent","protective","strategic"]',
 'Runs the Casablanca Continental. Currently in New York on undisclosed business. Her two Belgian Malinois are technically registered as guests.',
 7, 'Arrived Day 1, evening. Requested a quiet room and no visitors.'),
('The Adjudicator', NULL, 'Senior Adjudicator, High Table', 7, 'active', 90,
 '["precise","unyielding","fair_in_their_own_way","terrifying"]',
 'Speaks for the High Table. When they arrive, balances must be settled. Currently just passing through. Nobody believes that.',
 NULL, 'Not yet checked in. Expected.'),
('Koji Shimazu', NULL, 'Envoy of the Osaka Continental', 6, 'active', 65,
 '["honorable","conflicted","skilled","old_school"]',
 'Sent by the Osaka Continental on a diplomatic mission. The specifics are unclear. He seems uncomfortable in New York.',
 4, 'Arrived Day 1, afternoon. Has been in the dining room since, barely eating.'),
('Viktor Levkin', 'The Accountant', NULL, 3, 'active', 55,
 '["meticulous","nervous","valuable","desperate"]',
 'Ruska Roma numbers man. Showed up asking for sanctuary. Claims his own family wants him dead. Carries a ledger he will not let anyone touch.',
 NULL, 'Waiting in the lobby. Needs a room. Looks like he has not slept in days.'),
('Isabella Rosetti', 'La Contessa', 'Camorra Underboss', 4, 'active', 72,
 '["elegant","ruthless","cultured","patient"]',
 'Second in command of the Camorra''s New York operations. Officially here for a social visit. Has asked for an introduction to Sofia.',
 2, 'Arrived Day 1, evening. Already holding court in the lounge.'),
('Tick Tock Man', NULL, NULL, 5, 'active', 40,
 '["eccentric","reliable","everywhere","knows_things"]',
 'One of the Bowery King''s top lieutenants. Appears when least expected. Communicates in riddles half the time.',
 NULL, 'Sent a message via pigeon. Yes, actual pigeon. He wants a meeting.'),
('Dr. Elara Voss', 'The Doctor', 'Continental Physician', 2, 'active', 80,
 '["calm","skilled","sardonic","has_seen_everything"]',
 'The hotel doctor. Patches bullet wounds at 3 AM without blinking. Has a dry wit and an unsettlingly steady hand.',
 6, 'Always on call. Currently treating a kitchen accident.'),
('Marcel', 'The Sommelier', 'Continental Sommelier', 2, 'active', 70,
 '["knowledgeable","enthusiastic","particular","connected"]',
 'Weapons specialist who speaks about firearms the way others speak about wine.',
 5, 'Excited about a new shipment. Has been reorganizing the armory all week.');

-- ============================================================================
-- INITIAL RELATIONSHIPS
-- ============================================================================
INSERT INTO relationships (character_a_id, character_b_id, type, strength, public_known, origin_story) VALUES
((SELECT id FROM characters WHERE name='Winston'),
 (SELECT id FROM characters WHERE name='Charon'),
 'ally', 95, true, 'Decades of service together. Charon has been Winston''s right hand since before anyone can remember.'),
((SELECT id FROM characters WHERE name='Sofia Al-Azwar'),
 (SELECT id FROM characters WHERE name='Winston'),
 'grudging_respect', 60, true, 'They have history. Something happened in Casablanca years ago. Neither discusses it.'),
((SELECT id FROM characters WHERE name='Isabella Rosetti'),
 (SELECT id FROM characters WHERE name='Viktor Levkin'),
 'rival', 30, false, 'The Camorra wants what is in Viktor''s ledger. Isabella has been asking subtle questions.'),
((SELECT id FROM characters WHERE name='Koji Shimazu'),
 (SELECT id FROM characters WHERE name='Sofia Al-Azwar'),
 'neutral', 40, false, 'They met once in Osaka. The meeting did not go well.');

-- ============================================================================
-- INITIAL DEBTS
-- ============================================================================
INSERT INTO debts_markers (creditor_id, debtor_id, marker_type, description, value, status, created_day) VALUES
((SELECT id FROM characters WHERE name='Sofia Al-Azwar'),
 (SELECT id FROM characters WHERE name='Winston'),
 'marker', 'For services rendered during the Casablanca incident. Winston asked. Sofia delivered.', 7, 'outstanding', 0),
((SELECT id FROM characters WHERE name='Isabella Rosetti'),
 (SELECT id FROM characters WHERE name='Tick Tock Man'),
 'favor', 'The Bowery network provided intelligence on a Camorra rival. Isabella has not yet repaid.', 4, 'outstanding', 0);

-- ============================================================================
-- INITIAL EVENTS (Day 1)
-- ============================================================================
INSERT INTO events (day, phase, event_type, title, description, location_id, severity, is_public) VALUES
(1, 'afternoon', 'arrival', 'Koji Shimazu Arrives',
 'An envoy from the Osaka Continental arrived without advance notice. He presented proper credentials and requested a table in the dining room.',
 (SELECT id FROM locations WHERE name='The Dining Room'), 3, true),
(1, 'evening', 'arrival', 'Sofia Al-Azwar Checks In',
 'The Director of the Casablanca Continental arrived with two Belgian Malinois and minimal luggage. Requested Room 818. Specifically asked about the fire exits.',
 (SELECT id FROM locations WHERE name='The Front Desk'), 4, true),
(1, 'evening', 'arrival', 'Isabella Rosetti Arrives',
 'The Camorra underboss made an entrance. Full entourage, which she dismissed at the door per hotel rules. Went straight to the lounge.',
 (SELECT id FROM locations WHERE name='The Lounge'), 3, true),
(1, 'evening', 'request', 'Viktor Levkin Seeks Sanctuary',
 'A disheveled man claiming to be Viktor Levkin of the Ruska Roma appeared at the front desk requesting a room and protection. He says his own people are hunting him.',
 (SELECT id FROM locations WHERE name='The Front Desk'), 6, false);

-- ============================================================================
-- LORE CHUNKS (for semantic retrieval)
-- ============================================================================
INSERT INTO lore_chunks (category, title, content, tags, canon_level) VALUES
('history', 'The Founding of The Continental',
 'The Continental Hotel was established in 1888 as a neutral meeting ground for the nascent criminal underworld of New York City. The original charter, signed by seven founding families, established the core principle: no business on hotel grounds. The building itself predates the hotel, having served as a private club for Gilded Age industrialists whose enterprises were not entirely above board.',
 ARRAY['founding','history','charter','origins'], 'established'),
('tradition', 'The Marker System',
 'Blood markers are the most sacred instruments in the underworld. A marker represents an absolute debt—a life owed, a service that cannot be refused. They are physical objects: small medallions split in two, one half held by the creditor, one by the debtor. When the creditor presents both halves together, the debt is called. To refuse a called marker is to be declared excommunicado. There is no appeal.',
 ARRAY['markers','debts','traditions','blood_oath'], 'established'),
('tradition', 'Continental Coins',
 'Gold coins serve as the universal currency of the underworld. Each coin is worth a specific service: a room, a drink, a favor, a clean weapon, medical attention. The coins cannot be counterfeited—the alloy is specific, the stamp is verified, and the serial numbers are tracked. They are not money. They are social contracts made physical.',
 ARRAY['coins','currency','economy','services'], 'established'),
('world_building', 'The High Table Structure',
 'The High Table consists of twelve seats, each representing a major sphere of criminal enterprise. The seats are hereditary in some cases, earned in others, and seized by force more often than anyone admits. The Table does not govern day-to-day operations. It sets rules, arbitrates disputes between major factions, and enforces the fundamental order that keeps the underworld from collapsing into chaos. The Adjudicators are its enforcement arm.',
 ARRAY['high_table','governance','power','structure'], 'established'),
('tradition', 'Excommunicado',
 'To be declared excommunicado is to become a non-person in the underworld. All services are revoked: no Continental, no doctor, no weapons, no safe passage. An open contract is issued—anyone may collect. Most excommunicado declarations are death sentences, though some of the most resourceful have survived. The declaration requires a formal pronouncement and a one-hour grace period, a tradition that dates to the original charter.',
 ARRAY['excommunicado','punishment','rules','death'], 'established'),
('location_lore', 'The Continental Bar — Unwritten Rules',
 'The bar has its own customs beyond the official hotel rules. You do not approach someone''s table uninvited. You do not discuss business above a whisper. The bartender sees nothing and remembers everything. Tips are in gold coins, never cash. The piano player takes requests but never plays anything composed after 1965. These are not rules. They are understandings.',
 ARRAY['bar','customs','etiquette','social'], 'established'),
('proverb', 'On Rules and Consequences',
 'Rules exist to maintain order. Consequences exist to maintain rules. And the Continental exists to maintain the illusion that there is a difference between the two. — Attributed to the first Manager, circa 1920.',
 ARRAY['philosophy','rules','management','wisdom'], 'legendary'),
('faction_lore', 'The Bowery King''s Rise',
 'The Bowery King built his network from nothing. An excommunicado survivor himself, he created an intelligence empire from the forgotten people of New York: the homeless, the street performers, the subway dwellers. His network sees everything because nobody sees them. The High Table does not officially recognize his organization, which is both his greatest vulnerability and his greatest advantage.',
 ARRAY['bowery_king','network','intelligence','underground'], 'established'),
('character_lore', 'The Casablanca Incident',
 'What happened in Casablanca is spoken of only in fragments. Winston needed something done. Sofia did it. People died. A Continental was nearly compromised. A marker was issued. The details remain classified, but whatever occurred bound Winston and Sofia in a debt that neither seems eager to settle.',
 ARRAY['casablanca','winston','sofia','marker','classified'], 'classified'),
('ceremony', 'The Rite of Parley',
 'When hostile parties wish to negotiate on Continental grounds, they may invoke the Rite of Parley. Both parties must surrender their weapons to the Sommelier, agree to a time limit, and accept the Concierge as arbiter. The Concierge does not decide outcomes—they enforce fairness of process. If either party breaks parley, they are immediately in violation of Rule 1.',
 ARRAY['parley','negotiation','ceremony','concierge','protocol'], 'established');
