from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from resume_parser import parse_resume, get_logs
from resume_generator import generate_resume
from jd_optimizer import optimize_resume_for_jd
from ollama_utils import (
    ollama_extract_personal_details,
    ollama_extract_education,
    ollama_extract_work_experience,
    ollama_extract_projects,
    ollama_extract_skills,
    ollama_extract_sections,
)
from typing import Optional
import logging
import aiofiles

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

# In-memory store for parsed resume (for demo; replace with DB in prod)
parsed_resume_store = {}


@app.post("/upload_resume/")
async def upload_resume(file: UploadFile = File(...)):
    filename = os.path.basename(file.filename or "uploaded_resume")  # Sanitize filename
    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        # Use your parser to extract text from the resume file
        parsed = parse_resume(file_path)
        # Use ollama_utils to extract structured sections
        text = parsed.get("text", "")
        personal = await ollama_extract_personal_details(text)
        # education = await ollama_extract_education(text)
        # work_experience = await ollama_extract_work_experience(text)
        # projects = await ollama_extract_projects(text)
        # skills = await ollama_extract_skills(text)
        extrac_sections = await ollama_extract_sections(text)
        education = extrac_sections.get("education", [])
        work_experience = extrac_sections.get("work_experience", [])
        projects = extrac_sections.get("projects", [])
        skills = extrac_sections.get("skills", [])
        # Structure the parsed resume
        structured = {
            "personal_details": personal,
            "education": education,
            "work_experience": work_experience,
            "projects": projects,
            "skills": skills,
        }
        parsed_resume_store["resume"] = structured
        return JSONResponse(structured)
    except Exception as e:
        logging.exception("Failed to upload or parse resume")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/resume_sections/")
async def get_resume_sections():
    resume = parsed_resume_store.get("resume")
    if not resume:
        return JSONResponse({"error": "No resume parsed yet."}, status_code=404)
    return JSONResponse(resume)


@app.patch("/resume_sections/")
async def update_resume_sections(update: dict = Body(...)):
    resume = parsed_resume_store.get("resume")
    if not resume:
        return JSONResponse({"error": "No resume parsed yet."}, status_code=404)
    # Merge update into resume (shallow update for demo)
    for k, v in update.items():
        resume[k] = v
    parsed_resume_store["resume"] = resume
    return JSONResponse(resume)


@app.post("/optimize_resume/")
async def optimize_resume(parsed: dict = Body(...), jd: str = Body(...)):
    try:
        updated = optimize_resume_for_jd(parsed, jd)
        return JSONResponse(updated)
    except Exception as e:
        logging.exception("Failed to optimize resume")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/generate_resume/")
async def generate(
    parsed: dict = Body(...),
    template: str = Body("modern"),
    filetype: str = Body("docx"),
):
    try:
        output_path = generate_resume(parsed, template, filetype)
        return {"download_url": f"/download/{os.path.basename(output_path)}"}
    except Exception as e:
        logging.exception("Failed to generate resume")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/download/{filename}")
async def download(filename: str):
    file_path = os.path.join(GENERATED_DIR, filename)
    return FileResponse(file_path, filename=filename)


@app.get("/logs/")
async def fetch_logs():
    return JSONResponse({"logs": get_logs()})
