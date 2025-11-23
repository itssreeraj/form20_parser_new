-- =========================================================
--  Election Analysis DB Schema (PostgreSQL)
--  - Lok Sabha & Assembly constituencies
--  - Localbodies & wards
--  - Polling stations (with localbody/ward mapping)
--  - Form 20 booth results (Lok Sabha)
--  - Localbody election results (wards)
--  - Localbody ↔ Assembly mapping
-- =========================================================

-- You can wrap this in a separate schema if you like:
-- CREATE SCHEMA election;
-- SET search_path TO election;

-- =========================================================
-- 1. Core Constituencies
-- =========================================================

CREATE TABLE loksabha_constituency (
    id          BIGSERIAL PRIMARY KEY,
    ls_code     VARCHAR(10) UNIQUE NOT NULL,   -- e.g. "01", "Attingal"
    name        VARCHAR(150) NOT NULL,
    state       VARCHAR(100) NOT NULL DEFAULT 'Kerala'
);

CREATE TABLE assembly_constituency (
    id          BIGSERIAL PRIMARY KEY,
    ac_code     VARCHAR(10) UNIQUE NOT NULL,   -- e.g. "096"
    name        VARCHAR(150) NOT NULL,
    ls_id       INTEGER NOT NULL REFERENCES loksabha_constituency(id)
);

CREATE INDEX idx_ac_ls ON assembly_constituency(ls_id);

-- =========================================================
-- 2. Localbody Hierarchy
-- =========================================================

CREATE TABLE district (
    id      BIGSERIAL PRIMARY KEY,
    name    VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE localbody (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    type        VARCHAR(50) NOT NULL,          -- corporation / municipality / block / gp etc.
    district_id INTEGER REFERENCES district(id)
);

CREATE INDEX idx_localbody_district ON localbody(district_id);

CREATE TABLE ward (
    id              BIGSERIAL PRIMARY KEY,
    localbody_id    INTEGER NOT NULL REFERENCES localbody(id),
    ward_num        VARCHAR(10) NOT NULL,
    ward_name       VARCHAR(200),

    UNIQUE (localbody_id, ward_num)
);

CREATE INDEX idx_ward_localbody ON ward(localbody_id);

-- =========================================================
-- 3. Polling Stations (PS)
--    - Linked to LS, AC
--    - Optionally to Localbody & Ward (for your mappings)
-- =========================================================

CREATE TABLE polling_station (
    id              BIGSERIAL PRIMARY KEY,
    ls_id           INTEGER NOT NULL REFERENCES loksabha_constituency(id),
    ac_id           INTEGER NOT NULL REFERENCES assembly_constituency(id),

    ps_number       INTEGER NOT NULL,          -- numeric part, e.g. 91
    ps_suffix       VARCHAR(5),                -- A/B/C (part booths)
    ps_number_raw   VARCHAR(20),               -- e.g. "91A"

    name            TEXT,                      -- from polling station list PDF

    localbody_id    INTEGER REFERENCES localbody(id),
    ward_id         INTEGER REFERENCES ward(id)
);

CREATE UNIQUE INDEX polling_station_unique_idx
    ON polling_station (ac_id, ps_number, COALESCE(ps_suffix, ''));

CREATE INDEX idx_ps_ac       ON polling_station(ac_id);
CREATE INDEX idx_ps_ls       ON polling_station(ls_id);
CREATE INDEX idx_ps_lb       ON polling_station(localbody_id);
CREATE INDEX idx_ps_ward     ON polling_station(ward_id);

-- =========================================================
-- 4. Localbody ↔ Assembly Mapping
--    Useful when localbody spans multiple ACs;
--    you can assign a "primary" AC, or multiple with weights later.
-- =========================================================

CREATE TABLE localbody_ac_mapping (
    id              BIGSERIAL PRIMARY KEY,
    localbody_id    INTEGER NOT NULL REFERENCES localbody(id),
    ac_id           INTEGER NOT NULL REFERENCES assembly_constituency(id),

    -- Optionally: percentage of wards/booths that fall in this AC
    overlap_weight  NUMERIC(5,2),  -- can be NULL, or 100.00 for fully inside

    UNIQUE (localbody_id, ac_id)
);

CREATE INDEX idx_lb_ac_lb ON localbody_ac_mapping(localbody_id);
CREATE INDEX idx_lb_ac_ac ON localbody_ac_mapping(ac_id);

-- =========================================================
-- 5. Alliances, Parties, Candidates (Lok Sabha)
-- =========================================================

CREATE TABLE alliance (
    id      BIGSERIAL PRIMARY KEY,
    name    VARCHAR(20) UNIQUE NOT NULL,       -- LDF / UDF / NDA / IND / OTH
    color   VARCHAR(10)                        -- e.g. "#ff0000" for charts
);

CREATE TABLE party (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,  -- "Indian National Congress"
    short_name  VARCHAR(20),                   -- "INC"
    alliance_id INTEGER REFERENCES alliance(id)
);

CREATE INDEX idx_party_alliance ON party(alliance_id);

CREATE TABLE candidate (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    party_id        INTEGER REFERENCES party(id),
    ls_id           INTEGER REFERENCES loksabha_constituency(id),
    election_year   INTEGER NOT NULL,

    UNIQUE (name, ls_id, election_year)
);

CREATE INDEX idx_candidate_ls   ON candidate(ls_id);
CREATE INDEX idx_candidate_year ON candidate(election_year);

-- =========================================================
-- 6. Form 20 – Booth-wise Votes (Lok Sabha)
-- =========================================================

-- Per candidate per booth
CREATE TABLE booth_votes (
    id              BIGSERIAL PRIMARY KEY,
    ps_id           INTEGER NOT NULL REFERENCES polling_station(id),
    candidate_id    INTEGER NOT NULL REFERENCES candidate(id),
    votes           INTEGER NOT NULL,
    year            INTEGER NOT NULL,

    UNIQUE (ps_id, candidate_id, year)
);

CREATE INDEX idx_bv_ps        ON booth_votes(ps_id);
CREATE INDEX idx_bv_candidate ON booth_votes(candidate_id);
CREATE INDEX idx_bv_year      ON booth_votes(year);

-- Per booth totals (valid, rejected, NOTA)
CREATE TABLE booth_totals (
    id              BIGSERIAL PRIMARY KEY,
    ps_id           INTEGER NOT NULL REFERENCES polling_station(id),
    total_valid     INTEGER NOT NULL,
    rejected        INTEGER NOT NULL,
    nota            INTEGER NOT NULL,
    year            INTEGER NOT NULL,

    UNIQUE (ps_id, year)
);

CREATE INDEX idx_bt_ps   ON booth_totals(ps_id);
CREATE INDEX idx_bt_year ON booth_totals(year);

-- =========================================================
-- 7. Localbody Election Results (future localbody elections)
-- =========================================================

-- Candidates contesting localbody elections (e.g. GP/Muni)
CREATE TABLE lb_candidate (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    party_id        INTEGER REFERENCES party(id),
    localbody_id    INTEGER REFERENCES localbody(id),
    election_year   INTEGER NOT NULL
);

CREATE INDEX idx_lb_candidate_lb   ON lb_candidate(localbody_id);
CREATE INDEX idx_lb_candidate_year ON lb_candidate(election_year);

-- Ward-level localbody election results
CREATE TABLE lb_ward_results (
    id              BIGSERIAL PRIMARY KEY,
    ward_id         INTEGER NOT NULL REFERENCES ward(id),
    candidate_id    INTEGER NOT NULL REFERENCES lb_candidate(id),
    votes           INTEGER NOT NULL,
    election_year   INTEGER NOT NULL,

    UNIQUE (ward_id, candidate_id, election_year)
);

CREATE INDEX idx_lb_wr_ward   ON lb_ward_results(ward_id);
CREATE INDEX idx_lb_wr_year   ON lb_ward_results(election_year);

=========================================================
8. Helpful Views (optional, can be created later)
=========================================================

Example view: LS-level candidate totals from booth_votes
(You can uncomment and adjust when needed)

CREATE VIEW ls_candidate_totals AS
SELECT 
    c.ls_id,
    c.id AS candidate_id,
    c.name AS candidate_name,
    SUM(bv.votes) AS total_votes
FROM booth_votes bv
JOIN candidate c ON c.id = bv.candidate_id
GROUP BY c.ls_id, c.id, c.name;

Example view: Localbody-level candidate totals (Lok Sabha)

CREATE VIEW lb_candidate_totals_ls AS
SELECT
    ps.localbody_id,
    lb.name AS localbody_name,
    c.id AS candidate_id,
    c.name AS candidate_name,
    SUM(bv.votes) AS total_votes
FROM booth_votes bv
JOIN polling_station ps ON ps.id = bv.ps_id
JOIN localbody lb ON lb.id = ps.localbody_id
JOIN candidate c ON c.id = bv.candidate_id
GROUP BY ps.localbody_id, lb.name, c.id, c.name;


------------------------------------------------------------
-- Make ALL primary key IDs use BIGINT
------------------------------------------------------------

-- 1. alliance.id
ALTER TABLE alliance 
    ALTER COLUMN id TYPE BIGINT;

-- fix sequence if exists
ALTER SEQUENCE IF EXISTS alliance_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 2. party.id
ALTER TABLE party 
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS party_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 3. candidate.id
ALTER TABLE candidate
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS candidate_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 4. loksabha_constituency.id
ALTER TABLE loksabha_constituency
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS loksabha_constituency_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 5. assembly_constituency.id
ALTER TABLE assembly_constituency
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS assembly_constituency_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 6. district.id
ALTER TABLE district
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS district_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 7. localbody.id
ALTER TABLE localbody
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS localbody_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 8. ward.id
ALTER TABLE ward
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS ward_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 9. polling_station.id
ALTER TABLE polling_station
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS polling_station_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 10. booth_votes.id
ALTER TABLE booth_votes
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS booth_votes_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 11. booth_totals.id
ALTER TABLE booth_totals
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS booth_totals_id_seq
    AS BIGINT;

------------------------------------------------------------

-- 12. localbody_ac_mapping.id
ALTER TABLE localbody_ac_mapping
    ALTER COLUMN id TYPE BIGINT;

ALTER SEQUENCE IF EXISTS localbody_ac_mapping_id_seq
    AS BIGINT;

------------------------------------------------------------
-- Foreign key columns referencing these tables also need to be BIGINT
------------------------------------------------------------

-- candidate.party_id
ALTER TABLE candidate
    ALTER COLUMN party_id TYPE BIGINT;

ALTER TABLE candidate
    ALTER COLUMN ls_id TYPE BIGINT;

-- assembly_constituency.ls_id
ALTER TABLE assembly_constituency
    ALTER COLUMN ls_id TYPE BIGINT;

-- localbody.district_id
ALTER TABLE localbody
    ALTER COLUMN district_id TYPE BIGINT;

-- ward.localbody_id
ALTER TABLE ward
    ALTER COLUMN localbody_id TYPE BIGINT;

-- polling_station.ls_id, ac_id, localbody_id, ward_id
ALTER TABLE polling_station
    ALTER COLUMN ls_id TYPE BIGINT;

ALTER TABLE polling_station
    ALTER COLUMN ac_id TYPE BIGINT;

ALTER TABLE polling_station
    ALTER COLUMN localbody_id TYPE BIGINT;

ALTER TABLE polling_station
    ALTER COLUMN ward_id TYPE BIGINT;

-- booth_votes.ps_id, candidate_id
ALTER TABLE booth_votes
    ALTER COLUMN ps_id TYPE BIGINT;

ALTER TABLE booth_votes
    ALTER COLUMN candidate_id TYPE BIGINT;

-- booth_totals.ps_id
ALTER TABLE booth_totals
    ALTER COLUMN ps_id TYPE BIGINT;

-- localbody_ac_mapping.localbody_id, ac_id
ALTER TABLE localbody_ac_mapping
    ALTER COLUMN localbody_id TYPE BIGINT;

ALTER TABLE localbody_ac_mapping
    ALTER COLUMN ac_id TYPE BIGINT;

------------------------------------------------------------
-- Done
------------------------------------------------------------
