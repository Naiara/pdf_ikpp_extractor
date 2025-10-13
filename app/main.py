from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
import os
import tempfile
from .extractor import extract_from_pdf

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0"}


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    # save to temporary file
    tmp_dir = os.getenv('TMPDIR', '/tmp')
    tmp_path = os.path.join(tmp_dir, file.filename)
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    with open(tmp_path, 'wb') as f:
        f.write(contents)

    try:
        data = extract_from_pdf(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    return JSONResponse(content=data)


@app.post("/extract_raw")
async def extract_raw(request: Request):
    """Accept raw PDF bytes in the request body (Content-Type: application/pdf).

    This endpoint is convenient when a client (e.g. n8n) can send the PDF as
    binary in the request body and does not want to use multipart/form-data.
    """
    content_type = request.headers.get('content-type', '')
    if 'pdf' not in content_type.lower():
        raise HTTPException(status_code=400, detail="Content-Type must be application/pdf")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")

    # write to temporary file and reuse extractor
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(body)
        tmp.flush()
        tmp_path = tmp.name

    try:
        data = extract_from_pdf(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    return JSONResponse(content=data)
