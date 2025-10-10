# PDF extractor for cursos formativos

Minimal app that extracts center name, center code, course name and participants (DNI + result) from textual PDFs in Spanish or Basque.

Build image:

```powershell
docker build -t pdf-extractor .
```

Run (default port 8083):

```powershell
docker run -p 8083:8083 -e PORT=8083 pdf-extractor
```

API: POST /extract multipart/form-data file field named `file`.

CLI for testing:

```powershell
docker run --rm -v C:\path\to\pdfs:/data -w /data pdf-extractor python cli.py ejemplo.pdf
```

Do not commit test PDFs / sensitive files
---------------------------------------

This repository may contain local sample PDFs for testing (for example `FROGA.pdf`). Before pushing to a remote git repository, make sure you do not commit these sample PDFs or any other sensitive files. A `.gitignore` is provided that excludes `*.pdf`, virtual environments, caches and common IDE files.

Initialize git and push (example):

```powershell
git init
git add .
git commit -m "Initial import: pdf extractor service"
# add remote and push
git remote add origin <your-remote-url>
git push -u origin main
```

