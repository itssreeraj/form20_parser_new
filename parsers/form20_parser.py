import camelot
import re

def parse_form20_pdf(pdf_path, ls_code, ac_code, election_year):

    print(f"\nParsing Form 20 (LATTICE) → LS {ls_code}, AC {ac_code}: {pdf_path}")

    # Read all pages with lattice
    tables = camelot.read_pdf(
        pdf_path,
        pages="all",
        flavor="lattice",
        line_scale=40
    )
    print(f"Found {len(tables)} tables via lattice")

    if len(tables) == 0:
        print("No tables found using lattice.")
        return {
            "ls": ls_code,
            "ac": ac_code,
            "candidates": [],
            "booth_votes": [],
            "booth_totals": []
        }

    candidates = []
    total_index = None
    header_parsed = False   # <-- detect header only once
    booth_votes = []
    booth_totals = []

    # -----------------------------------------------------------
    # Iterate through ALL tables on ALL pages
    # -----------------------------------------------------------
    for idx, t in enumerate(tables):
        df = t.df

        if df.shape[0] < 2 or df.shape[1] < 5:
            continue

        # clean first-cell (it may have newlines)
        first_cell = df.iloc[0, 0].replace("\n", " ").strip().lower()

        if not first_cell.startswith("serial"):
            continue  # skip metadata tables

        print(f"✔ Valid Form-20 table found on index {idx}")

        rows, cols = df.shape

        # -----------------------------------------------------------
        # Parse header only once (from the FIRST correct table)
        # -----------------------------------------------------------
        if not header_parsed:

            header_row0 = [c.replace("\n", " ").strip() for c in df.iloc[0].tolist()]
            header_row1 = [c.replace("\n", " ").strip() for c in df.iloc[1].tolist()]

            # Find TOTAL column in row0 or row1
            for i, cell in enumerate(header_row0):
                if re.search(r"total", cell, re.I):
                    total_index = i
                    break

            if total_index is None:
                for i, cell in enumerate(header_row1):
                    if re.search(r"total", cell, re.I):
                        total_index = i
                        break

            if total_index is None:
                print("Total column not found in this header. Skipping table.")
                continue

            # Candidates = row1 from col 2 up to (total_index - 1)
            candidates = header_row1[2:total_index]
            print("Candidates:", candidates)

            header_parsed = True  # <-- from now on, do NOT reparse candidates

        # -----------------------------------------------------------
        # Booth rows begin from row 2 on *every* page
        # -----------------------------------------------------------
        for r in range(2, rows):
            row = [c.replace("\n", " ").strip() for c in df.iloc[r].tolist()]

            if len(row) < total_index + 3:
                continue

            serial = row[0].strip()
            ps_raw = row[1].strip()

            # ----------------------------------------------------
            # CASE A: col0 contains merged values like "100 100"
            # ----------------------------------------------------
            if ps_raw == "" and re.fullmatch(r"\d+[A-Za-z]?\s+\d+[A-Za-z]?", serial):
                parts = serial.split()
                serial = parts[0]          # serial = first token
                ps_raw = parts[1]          # ps_raw = second token

            # ----------------------------------------------------
            # CASE B: col1 contains merged values like "100 100"
            # ----------------------------------------------------
            elif serial == "" and re.fullmatch(r"\d+[A-Za-z]?\s+\d+[A-Za-z]?", ps_raw):
                parts = ps_raw.split()
                serial = parts[0]
                ps_raw = parts[1]

            # ----------------------------------------------------
            # VALIDATION
            # ----------------------------------------------------
            if not re.fullmatch(r"\d+", serial):
                continue

            if not re.fullmatch(r"\d+[A-Za-z]?", ps_raw):
                continue

            m = re.match(r"(\d+)([A-Za-z]?)", ps_raw)
            ps_number = int(m.group(1))
            ps_suffix = m.group(2).upper() or ""

            # candidate votes
            cand_votes = []
            for i in range(len(candidates)):
                colindex = 2 + i
                try:
                    v = int(row[colindex])
                except:
                    v = 0
                cand_votes.append(v)

            # totals → Total, Rejected, NOTA
            def safe_int(v):
                try: return int(v)
                except: return 0

            total_valid = safe_int(row[total_index])
            rejected    = safe_int(row[total_index + 1])
            nota        = safe_int(row[total_index + 2])

            booth_totals.append({
                "ls": ls_code,
                "ac": ac_code,
                "ps_number_raw": ps_raw,
                "ps_number": ps_number,
                "ps_suffix": ps_suffix,
                "total_valid": total_valid,
                "rejected": rejected,
                "nota": nota,
                "year": election_year
            })

            for ci, votes in enumerate(cand_votes):
                booth_votes.append({
                    "ls": ls_code,
                    "ac": ac_code,
                    "ps_number_raw": ps_raw,
                    "ps_number": ps_number,
                    "ps_suffix": ps_suffix,
                    "candidate_name": candidates[ci],
                    "votes": votes,
                    "year": election_year
                })

    print(f"Final: {len(booth_votes)} booth×candidate rows parsed")
    print(f"Final: {len(booth_totals)} booth totals parsed\n")

    return {
        "ls": ls_code,
        "ac": ac_code,
        "candidates": candidates,
        "booth_votes": booth_votes,
        "booth_totals": booth_totals
    }
