import sys
import pdfplumber

def main():
    if len(sys.argv) < 2:
        print('Usage: python debug_text.py <file.pdf> [start_page]')
        sys.exit(1)
    path = sys.argv[1]
    start_page = int(sys.argv[2]) if len(sys.argv) >= 3 else 1
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            if i < start_page:
                continue
            text = page.extract_text() or ''
            print('--- PAGE', i, '---')
            for ln in text.splitlines():
                print(repr(ln))
            print()
            # limit to a few pages
            if i >= start_page + 4:
                break

if __name__ == '__main__':
    main()
