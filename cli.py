import sys
from app.extractor import extract_from_pdf
import json


def main():
    if len(sys.argv) < 2:
        print("Usage: python cli.py <file.pdf>")
        sys.exit(1)
    path = sys.argv[1]
    data = extract_from_pdf(path)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
