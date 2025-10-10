import re
from typing import List, Dict, Optional
import pdfplumber


def _clean_dni(value: str) -> str:
    if not value:
        return ""
    v = value.strip()
    # remove dots, spaces, hyphens
    v = re.sub(r"[.\-\s]", "", v)
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


def extract_from_pdf(path: str) -> Dict:
    """Extract required fields from text PDF and return dict.

    Strategy:
    - Read text per page, build list of non-empty lines.
    - Extract labels line-by-line splitting on ':' when possible.
    - Find participants section and collect lines that contain a DNI; from each such line extract DNI and result.
    """
    pages_text: List[str] = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            pages_text.append(p.extract_text() or "")

    full_text = "\n".join(pages_text)
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

    result = {
        "center_name": None,
        "center_code": None,
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
                result['center_name'] = ln.split(':', 1)[1].strip()
            else:
                # value might be next line
                if i + 1 < len(lines):
                    result['center_name'] = lines[i + 1].strip()
        # center code
        if label_code_es in low or label_code_eu in low or 'codigo de centro' in low:
            if ':' in ln:
                # take first numeric token after ':'
                after = ln.split(':', 1)[1].strip()
                m = re.search(r"(\d{4,})", after)
                if m:
                    result['center_code'] = m.group(1)
                else:
                    result['center_code'] = after.split()[0] if after.split() else None
            else:
                if i + 1 < len(lines):
                    m = re.search(r"(\d{4,})", lines[i + 1])
                    if m:
                        result['center_code'] = m.group(1)
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

    dni_re = re.compile(r"\b\d{7,8}[A-Za-z0-9]\b")

    participants: List[Dict] = []
    if start_idx is not None:
        for ln in lines[start_idx:]:
            # stop if we hit a likely footer or blank
            if ln.lower().startswith('yo,') or ln.lower().startswith('firma'):
                break
            # if line contains a DNI, parse it
            m = dni_re.search(ln)
            if m:
                dni = _clean_dni(m.group(0))
                # look for result in the same line (Apto/No apto/Gai/Ez gai)
                res = None
                if re.search(r"\b(apto|no apto|noapto)\b", ln, flags=re.IGNORECASE):
                    match = re.search(r"\b(no apto|noapto|apto)\b", ln, flags=re.IGNORECASE).group(1)
                    res = _normalize_result(match)
                elif re.search(r"\b(gai|ez gai|ezgai)\b", ln, flags=re.IGNORECASE):
                    match = re.search(r"\b(ez gai|ezgai|gai)\b", ln, flags=re.IGNORECASE).group(1)
                    res = _normalize_result(match)
                else:
                    # maybe result is at the end after multiple spaces; try last token
                    parts = ln.split()
                    if parts:
                        possible = parts[-1]
                        r = _normalize_result(possible)
                        if r is not None:
                            res = r

                participants.append({"dni": dni, "result": res})

    result['participants'] = participants

    return result

