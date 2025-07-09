from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from resume_parser import parse_resume
from resume_generator import generate_resume
from jd_optimizer import optimize_resume_for_jd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
GENERATED_DIR = "generated"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)


@app.post("/upload_resume/")
def upload_resume(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    parsed = parse_resume(file_path)
    return JSONResponse(parsed)


@app.post("/optimize_resume/")
def optimize_resume(parsed: dict = Form(...), jd: str = Form(...)):
    updated = optimize_resume_for_jd(parsed, jd)
    return JSONResponse(updated)


@app.post("/generate_resume/")
def generate(
    parsed: dict = Form(...),
    template: str = Form("modern"),
    filetype: str = Form("docx"),
):
    output_path = generate_resume(parsed, template, filetype)
    return {"download_url": f"/download/{os.path.basename(output_path)}"}


@app.get("/download/{filename}")
def download(filename: str):
    file_path = os.path.join(GENERATED_DIR, filename)
    return FileResponse(file_path, filename=filename)
