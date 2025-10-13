import re
from typing import List, Dict, Optional
import pdfplumber


def _clean_dni(value: str) -> str:
    if not value:
        return ""
    v = value.strip()
    # remove any non-alphanumeric characters (dots, spaces, hyphens, etc.)
    v = re.sub(r"[^0-9A-Za-z]", "", v)
    # normalize to uppercase (letters in DNI should be uppercase)
    v = v.upper()
    return v


def _normalize_result(value: str) -> Optional[bool]:
    if not value:
        return None
    v = value.strip().lower()
    # Spanish
    if v in ("apto", "a"):
        return True
    if v in ("no apto", "no", "no_apto", "noapto"):
        return False
    # Euskera
    if v in ("gai",):
        return True
    if v in ("ez gai", "ezgai"):
        return False
    # fallback contains
    if "no apt" in v or "noapto" in v:
        return False
    if "apto" in v:
        return True
    if "ez gai" in v:
        return False
    if "gai" in v and "ez" not in v:
        return True
    return None


def parse_participants_from_lines(lines: List[str], start_idx: int) -> List[Dict]:
    """Parse participants from pre-split lines starting at start_idx.

    This helper merges up to 2 following lines when a row is split so rows
    aren't counted twice.
    """
    participants: List[Dict] = []
    idx = start_idx
    while idx < len(lines):
        ln = lines[idx]
        # stop if we hit a likely footer or signature
        if ln.lower().startswith('yo,') or ln.lower().startswith('firma'):
            break

        m = dni_re.search(ln)
        if m:
            student_id = _clean_dni(m.group(0))
            qualified = None
            m_qual = re.search(r"\b(ez[-\s]?gai|gai|no apto|noapto|apto)\b\s*$", ln, flags=re.IGNORECASE)
            consumed = 0
            qualified_raw = None
            if m_qual:
                qualified_raw = m_qual.group(0).strip().strip('.,;:')
                qualified = _normalize_result(qualified_raw)
                consumed = 1
            else:
                # Try merging with the next 1-2 lines in case the row was split by linebreaks
                for look_ahead in (1, 2):
                    next_idx = idx + look_ahead
                    if next_idx < len(lines):
                        combined = ln + " " + lines[next_idx]
                        m_qual2 = re.search(r"\b(ez[-\s]?gai|gai|no apto|noapto|apto)\b\s*$", combined, flags=re.IGNORECASE)
                        if m_qual2:
                            qualified_raw = m_qual2.group(0).strip().strip('.,;:')
                            qualified = _normalize_result(qualified_raw)
                            consumed = 1 + look_ahead
                            break

            participants.append({"student_id": student_id, "qualified": qualified, "qualified_raw": qualified_raw})
            # advance index by number of consumed lines (at least 1)
            if consumed > 0:
                idx += consumed
                continue
        idx += 1

    return participants


def parse_participants_from_table(table: List[List[str]]) -> List[Dict]:
    """Parse participants from a table (list of rows, each row is list of cell texts).

    Heuristic: join cells with space and treat that as the row text. Then extract
    the DNI token and qualification (expected at end of the joined row).
    """
    participants: List[Dict] = []

    # Strict parsing per user's specification:
    # - find header column named exactly 'DNI' or 'NANa' (case-insensitive) within first 5 rows
    # - student_id is taken ONLY from that column; if empty -> skip row
    # - qualified is taken ONLY from the LAST column of the row
    participants = []
    header_col_idx = None
    header_row_idx = None
    if not table:
        return participants
    max_header_scan = min(5, len(table))
    header_pattern = re.compile(r"\b(dni|nan|nana)\b", flags=re.IGNORECASE)
    for r in range(max_header_scan):
        row_lower = [(cell or "").strip().lower() for cell in table[r]]
        for i, cell in enumerate(row_lower):
            if header_pattern.search(cell):
                header_col_idx = i
                header_row_idx = r
                break
        if header_col_idx is not None:
            break

    # if no DNI/NAN header found, return empty (we expect a well-formed table)
    if header_col_idx is None:
        return participants

    # process rows after header row
    rows_to_process = table[header_row_idx + 1:]
    for row in rows_to_process:
        # ensure the row has the DNI cell
        if header_col_idx >= len(row):
            continue
        raw_dni = (row[header_col_idx] or "").strip()
        student_id = _clean_dni(raw_dni)
        if not student_id:
            # skip row if DNI cell empty after cleaning
            continue

        # qualified comes from the last column
        if len(row) == 0:
            qualified = None
        else:
            qual_raw = (row[-1] or "").strip()
            qualified = _normalize_result(qual_raw)

        participants.append({"student_id": student_id, "qualified": qualified})
    return participants
# Module-level permissive DNI token extractor (used by parsing helpers)
# Accept alphanumeric tokens (and hyphens) of length 5-12 that contain at least one digit.
dni_re = re.compile(r"\b(?=[A-Za-z0-9-]{5,12}\b)(?=[A-Za-z0-9-]*\d)[A-Za-z0-9-]{5,12}\b")


def extract_from_pdf(path: str) -> Dict:
    """Extract required fields from text PDF and return dict.

    Strategy:
    - Read text per page, build list of non-empty lines.
    - Extract labels line-by-line splitting on ':' when possible.
    - Find participants section and collect lines that contain a DNI; from each such line extract DNI and result.
    """
    pages_text: List[str] = []
    # store per-page lines to map header location to a page
    pages_lines_list: List[List[str]] = []
    # store tables along with the page index where they were found
    tables_found: List[tuple] = []  # list of (page_index, table)
    with pdfplumber.open(path) as pdf:
        for p_idx, p in enumerate(pdf.pages):
            text = p.extract_text() or ""
            pages_text.append(text)
            page_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            pages_lines_list.append(page_lines)
            try:
                page_tables = p.extract_tables() or []
                for t in page_tables:
                    norm = [[cell or "" for cell in row] for row in t]
                    tables_found.append((p_idx, norm))
            except Exception:
                # ignore table extraction errors
                pass

    full_text = "\n".join(pages_text)
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

    result = {
        "school_name": None,
        "school_id": None,
        "course_name": None,
        "participants": []
    }

    # label variants
    label_center_es = "nombre oficial del centro"
    label_center_eu = "ikastetxearen izen ofiziala"
    label_code_es = "código de centro"
    label_code_eu = "ikastetxearen kodea"
    label_course_es = "título de la actividad formativa"
    label_course_eu = "prestakuntza-jardueraren izena"

    # extract labels by scanning lines
    for i, ln in enumerate(lines):
        low = ln.lower()
        # center name
        if label_center_es in low or label_center_eu in low:
            # split on ':' and take remainder
            if ':' in ln:
                result['school_name'] = ln.split(':', 1)[1].strip()
            else:
                # value might be next line
                if i + 1 < len(lines):
                    result['school_name'] = lines[i + 1].strip()
        # center code
        if label_code_es in low or label_code_eu in low or 'codigo de centro' in low:
            if ':' in ln:
                # take first numeric token after ':'
                after = ln.split(':', 1)[1].strip()
                m = re.search(r"(\d{4,})", after)
                if m:
                    result['school_id'] = m.group(1)
                else:
                    result['school_id'] = after.split()[0] if after.split() else None
            else:
                if i + 1 < len(lines):
                    m = re.search(r"(\d{4,})", lines[i + 1])
                    if m:
                        result['school_id'] = m.group(1)
        # course name
        if label_course_es in low or label_course_eu in low:
            if ':' in ln:
                result['course_name'] = ln.split(':', 1)[1].strip()
            else:
                if i + 1 < len(lines):
                    result['course_name'] = lines[i + 1].strip()

    # find participants section
    header_es = "datos personales de los/las participantes en la actividad formativa"
    header_eu = "prestakuntza-jarduerako parte-hartzaileen datu pertsonalak"
    start_idx = None
    for idx, ln in enumerate(lines):
        l = ln.lower()
        if header_es in l or header_eu in l:
            start_idx = idx + 1
            break

    # Use module-level `dni_re` (permissive token extractor). Try parsing from
    # detected tables first because table rows map 1:1 to logical rows.
    participants: List[Dict] = []

    table_participants: List[Dict] = []
    # If we found a start index (header), try to locate the page containing it
    selected_table = None
    if start_idx is not None and tables_found:
        # determine which page contains start_idx by walking pages_lines_list
        cum = 0
        page_of_header = None
        for p_idx, plines in enumerate(pages_lines_list):
            if start_idx >= cum and start_idx < cum + len(plines):
                page_of_header = p_idx
                break
            cum += len(plines)

        # prefer first table on same page, otherwise first table on later pages
        if page_of_header is not None:
            for (p_idx, table) in tables_found:
                if p_idx == page_of_header:
                    selected_table = table
                    break
            if selected_table is None:
                for (p_idx, table) in tables_found:
                    if p_idx > page_of_header:
                        selected_table = table
                        break

    # if we have a selected table, parse it and also try to append tables from
    # subsequent pages when they appear to be a continuation (i.e. parsing them
    # yields participant rows). This handles tables that span multiple pages.
    if selected_table is not None:
        table_participants = parse_participants_from_table(selected_table)
        # find the page index of the selected table
        sel_page_idx = None
        for p_idx, table in tables_found:
            if table is selected_table:
                sel_page_idx = p_idx
                break
        # append tables on following pages if they parse to participants
        if sel_page_idx is not None:
            for (p_idx, table) in tables_found:
                if p_idx > sel_page_idx:
                    parsed_next = parse_participants_from_table(table)
                    if parsed_next:
                        table_participants.extend(parsed_next)
                    else:
                        # stop at first non-matching table to avoid grabbing unrelated tables
                        break

    if table_participants:
        participants = table_participants
    else:
        if start_idx is not None:
            # fallback to line-based parsing is kept for debugging only;
            # commented out in production logic per user request.
            # participants = parse_participants_from_lines(lines, start_idx)
            pass

    # assign row_id sequentially starting at 1
    for idx, p in enumerate(participants, start=1):
        p['row_id'] = idx
    result['participants'] = participants

    return result

