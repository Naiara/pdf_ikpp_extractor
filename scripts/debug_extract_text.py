import pdfplumber

PDF_PATH = "FROGA.pdf"

def main():
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            print(f"--- PAGE {i+1} (first 1000 chars) ---")
            print(text[:1000])
            print()
            # stop after a few pages for brevity
            if i >= 4:
                break

if __name__ == '__main__':
    main()
