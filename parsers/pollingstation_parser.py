import re
import fitz  # PyMuPDF

def parse_polling_station_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    rows = []

    district_code = None
    district_name = None
    ac_code = None
    ac_name = None

    pending_ps = None

    # Extract metadata from first page only
    first_text = doc[0].get_text("text")
    for line in first_text.split("\n"):
        line_clean = line.strip().replace("\xa0", " ")
        
        # DISTRICT NO & NAME : 4 - KOZHIKODE
        m_dist = re.search(r"DISTRICT\s+NO\s*&\s*NAME\s*:\s*(\d+)\s*-\s*(.+)", line_clean, re.I)
        if m_dist:
            district_code = m_dist.group(1).strip()
            district_name = m_dist.group(2).strip()
        
        # LAC NO & NAME : 23 - QUILANDY
        m_ac = re.search(r"LAC\s+NO\s*&\s*NAME\s*:\s*(\d+)\s*-\s*(.+)", line_clean, re.I)
        if m_ac:
            ac_code = m_ac.group(1).strip()
            ac_name = m_ac.group(2).strip()

    print(f"Extracted District = {district_code} - {district_name}")
    print(f"Extracted AC = {ac_code} - {ac_name}")

    # Parse polling station rows
    for page in doc:
        lines = page.get_text("text").split("\n")

        for raw in lines:
            line = raw.strip()
            line = line.replace("\xa0", " ")
            line = re.sub(r"\s+", " ", line)

            if not line:
                continue

            lower = line.lower()
            if any(h in lower for h in [
                "district", "lac", "block", "taluk", "polling station", "sl no", "ps no"
            ]):
                continue

            # Case A — single-line "123 Name"
            m_single = re.match(r"^(\d{1,3}[A-Za-z]?)\s+(.*)$", line)
            if m_single:
                ps_raw = m_single.group(1)
                name = m_single.group(2).strip()

                m2 = re.match(r"(\d+)([A-Za-z]?)$", ps_raw)
                if not m2:
                    continue

                rows.append({
                    "district_code": district_code,
                    "district_name": district_name,
                    "ac_code": ac_code,
                    "ac_name": ac_name,
                    "ps_number_raw": ps_raw,
                    "ps_number": int(m2.group(1)),
                    "ps_suffix": m2.group(2).upper(),
                    "polling_station_name": name,
                })
                continue

            # Case B — number only (first line of 2-line)
            if re.fullmatch(r"\d{1,3}[A-Za-z]?", line):
                pending_ps = line
                continue

            # Case C — name only (second line)
            if pending_ps:
                ps_raw = pending_ps
                pending_ps = None

                m2 = re.match(r"(\d+)([A-Za-z]?)$", ps_raw)
                if not m2:
                    continue

                rows.append({
                    "district_code": district_code,
                    "district_name": district_name,
                    "ac_code": ac_code,
                    "ac_name": ac_name,
                    "ps_number_raw": ps_raw,
                    "ps_number": int(m2.group(1)),
                    "ps_suffix": m2.group(2).upper(),
                    "polling_station_name": line,
                })
                continue

    doc.close()
    return rows
