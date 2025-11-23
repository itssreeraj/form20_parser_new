import re
import fitz  # PyMuPDF

def parse_polling_station_pdf(pdf_path, ac_number):
    doc = fitz.open(pdf_path)
    rows = []

    pending_ps = None   # holds PS number until name arrives (two-line case)

    for page in doc:
        text = page.get_text("text")
        lines = text.split("\n")

        for raw in lines:
            line = raw.strip()

            # Normalize whitespace & invisible chars
            line = line.replace("\xa0", " ")
            line = re.sub(r"\s+", " ", line).strip()

            if not line:
                continue

            # Skip known header patterns
            lower = line.lower()
            if any(h in lower for h in [
                "district", "l a c", "lac no", "block", "taluk", "booth",
                "sl no", "ps no", "polling station name", "polling station"
            ]):
                continue

            # -----------------------------------------------------------
            # CASE A → SINGLE-LINE FORMAT (e.g., "1 Govt School")
            # -----------------------------------------------------------
            m_single = re.match(r"^(\d{1,3}[A-Za-z]?)\s+(.*)$", line)
            if m_single:
                ps_raw = m_single.group(1)
                name = m_single.group(2).strip()

                # extract number + suffix
                m2 = re.match(r"(\d+)([A-Za-z]?)$", ps_raw)
                if not m2:
                    continue

                ps_number = int(m2.group(1))
                ps_suffix = m2.group(2).upper() or ""

                rows.append({
                    "ac": ac_number,
                    "ps_number_raw": ps_raw,
                    "ps_number": ps_number,
                    "ps_suffix": ps_suffix,
                    "polling_station_name": name
                })

                print(f"[1-line] AC {ac_number}: PS {ps_raw} → {name}")
                pending_ps = None
                continue

            # -----------------------------------------------------------
            # CASE B → NUMBER-ONLY LINE (first line of two-line format)
            # -----------------------------------------------------------
            if re.fullmatch(r"\d{1,3}[A-Za-z]?", line):
                pending_ps = line
                continue

            # -----------------------------------------------------------
            # CASE C → NAME-ONLY LINE (second line of two-line format)
            # Use only if a pending PS exists
            # -----------------------------------------------------------
            if pending_ps:
                ps_raw = pending_ps
                name = line

                m2 = re.match(r"(\d+)([A-Za-z]?)$", ps_raw)
                if not m2:
                    pending_ps = None
                    continue

                ps_number = int(m2.group(1))
                ps_suffix = m2.group(2).upper() or ""

                rows.append({
                    "ac": ac_number,
                    "ps_number_raw": ps_raw,
                    "ps_number": ps_number,
                    "ps_suffix": ps_suffix,
                    "polling_station_name": name
                })

                print(f"[2-line] AC {ac_number}: PS {ps_raw} → {name}")
                pending_ps = None
                continue

            # -----------------------------------------------------------
            # OTHER LINES → ignored
            # -----------------------------------------------------------

    doc.close()
    return rows
