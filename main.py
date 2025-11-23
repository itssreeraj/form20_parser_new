import os
import csv

from parsers.form20_parser import parse_form20_pdf
from parsers.pollingstation_parser import parse_polling_station_pdf

FORM20_DIR = "form20_pdfs"
PS_DIR = "pollingstation_pdfs"

all_booths = []
all_candidates = set()       # will store placeholder names like "LS001_AC102_C1"
all_booth_votes = []
all_booth_totals = []


def get_ac_from_filename(fname: str) -> int:
    digits = "".join(c for c in fname if c.isdigit())
    return int(digits) if digits else 0


# ---------------------------
# 1. Polling Station Lists (ACxxx.pdf)
# ---------------------------
print("\n=== POLLING STATION LISTS ===")
for fname in os.listdir(PS_DIR):
    if not fname.lower().endswith(".pdf"):
        continue

    ac_code = get_ac_from_filename(fname)
    path = os.path.join(PS_DIR, fname)

    print(f"\n➡ AC {ac_code}: {fname}")
    booths = parse_polling_station_pdf(path)
    print(f"Parsed {len(booths)} polling stations for AC {ac_code}")
    all_booths.extend(booths)


# ---------------------------
# 2. Form 20 PDFs (grouped by LS folders)
# ---------------------------
print("\n=== FORM 20 PDFs ===")
for ls_folder in os.listdir(FORM20_DIR):
    ls_path = os.path.join(FORM20_DIR, ls_folder)
    if not os.path.isdir(ls_path):
        continue

    ls_code = ls_folder.replace("LS", "").strip() or ls_folder
    print(f"\nLS {ls_code} → folder {ls_folder}")

    for fname in os.listdir(ls_path):
        if not fname.lower().endswith(".pdf"):
            continue

        ac_code = "".join([c for c in fname if c.isdigit()])
        pdf_path = os.path.join(ls_path, fname)

        result = parse_form20_pdf(pdf_path, ls_code, ac_code, election_year=2024)

        # Build global placeholder candidate IDs so they can be unique per LS/AC/index.
        for cand_name in enumerate(result["candidates"], start=1):
            # Example key: "LS_Vadakara_AC_102_C1"
            key = f"LS_{ls_code}_AC{ac_code}_C{cand_name}"
            all_candidates.add(key)

        all_booth_votes.extend(result["booth_votes"])
        all_booth_totals.extend(result["booth_totals"])


# ---------------------------
# 3. OUTPUT CSVs
# ---------------------------
os.makedirs("output", exist_ok=True)

# 3.1 booths.csv
with open("output/booths.csv", "w", newline="", encoding="utf8") as f:
    w = csv.DictWriter(f, fieldnames=[
        "district_code",
        "district_name",
        "ac_code",
        "ac_name",
        "ps_number_raw",
        "ps_number",
        "ps_suffix",
        "polling_station_name"
    ])
    w.writeheader()
    w.writerows(all_booths)

# 3.2 candidates.csv (placeholder IDs)
with open("output/candidates.csv", "w", newline="", encoding="utf8") as f:
    w = csv.writer(f)
    w.writerow(["candidate_key"])
    for c in sorted(all_candidates):
        w.writerow([c])

# 3.3 form20_parsed.csv – booth × candidate_index votes
with open("output/form20_parsed.csv", "w", newline="", encoding="utf8") as f:
    w = csv.DictWriter(f, fieldnames=[
        "ls",
        "ac",
        "serial_no",
        "ps_number_raw",
        "ps_number",
        "ps_suffix",
        "candidate_name",
        "votes",
        "year"
    ])
    w.writeheader()
    w.writerows(all_booth_votes)

# 3.4 booth_totals.csv – per-booth totals
with open("output/booth_totals.csv", "w", newline="", encoding="utf8") as f:
    w = csv.DictWriter(f, fieldnames=[
        "ls",
        "ac",
        "serial_no",
        "ps_number_raw",
        "ps_number",
        "ps_suffix",
        "total_valid",
        "rejected",
        "nota",
        "year"
    ])
    w.writeheader()
    w.writerows(all_booth_totals)

print("\nParsing completed successfully!")
print("output/booths.csv")
print("output/candidates.csv")
print("output/form20_parsed.csv")
print("output/booth_totals.csv")
