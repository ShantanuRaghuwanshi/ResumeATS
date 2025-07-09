import os
import logging
import json
import re
from typing import Dict
from ollama import chat, AsyncClient
from models.resume import PersonalDetails, ResumeSections

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Use a custom client to allow custom host (API URL)
ollama_client = AsyncClient(host=OLLAMA_API_URL)


async def ollama_extract_personal_details(text: str) -> Dict:
    details = {"name": "", "contact": "", "linkedin": ""}
    try:
        messages = [
            {
                "role": "system",
                "content": "Extract the name, contact email, and LinkedIn URL from the following resume text. Return as JSON with keys: name, contact, linkedin.",
            },
            {"role": "user", "content": text},
        ]
        # Use Ollama Python SDK
        logging.info("Calling Ollama for personal details...")
        response = await ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format=PersonalDetails.model_json_schema(),
        )
        llm_details = response["message"]["content"]
        logging.info(f"Ollama response for personal details: {llm_details}")
        try:
            pd = PersonalDetails.model_validate_json(llm_details)
            details = pd.model_dump()
        except Exception as e:
            logging.error(f"Error parsing personal details with Pydantic: {e}")
        logging.info(f"Ollama personal details: {details}")
    except Exception as e:
        logging.error(f"Ollama personal details error: {e}")
    return details


async def ollama_extract_sections(text: str) -> Dict:
    sections = {
        "education": [],
        "work_experience": [],
        "projects": [],
        "skills": [],
    }
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract the following sections from the resume text: education, work_experience, projects, skills. "
                    "Return as JSON with these keys. "
                    "For education, provide a list of objects with university, degree, location, from_year, to_year, and gpa. "
                    "For work_experience, provide a list of objects with title, company, location, from_year, to_year, summary, and a list of projects (each with name, summary, and bullets). "
                    "For projects, provide a list of objects with name and bullets. "
                    "For skills, provide a list of strings."
                ),
            },
            {"role": "user", "content": text},
        ]
        logging.info("Calling Ollama for sections...")
        response = await ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format=ResumeSections.model_json_schema(),
        )
        llm_sections = response["message"]["content"]
        try:
            rs = ResumeSections.model_validate_json(llm_sections)
            sections = rs.model_dump()
        except Exception as e:
            logging.error(f"Error parsing sections with Pydantic: {e}")
        logging.info(f"Ollama sections: {sections}")
    except Exception as e:
        logging.error(f"Ollama sections error: {e}")
    return sections


async def ollama_extract_education(text: str):
    from models.resume import EducationEntry

    education = []
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract the education section from the resume text. "
                    "Return a list of objects with university, degree, location, from_year, to_year, and gpa."
                ),
            },
            {"role": "user", "content": text},
        ]
        logging.info("Calling Ollama for education...")
        response = await ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format={"type": "array", "items": EducationEntry.model_json_schema()},
        )
        llm_education = response["message"]["content"]
        try:
            education = [
                EducationEntry.model_validate_json(item)
                for item in json.loads(llm_education)
            ]
            education = [e.model_dump() for e in education]
        except Exception as e:
            logging.error(f"Error parsing education with Pydantic: {e}")
        logging.info(f"Ollama education: {education}")
    except Exception as e:
        logging.error(f"Ollama education error: {e}")
    return education


async def ollama_extract_work_experience(text: str):
    from models.resume import WorkExperienceEntry

    work_experience = []
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract the work experience section from the resume text. "
                    "Return a list of objects with title, company, location, from_year, to_year, summary, and a list of projects (each with name, summary, and bullets)."
                ),
            },
            {"role": "user", "content": text},
        ]
        logging.info("Calling Ollama for work experience...")
        response = await ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format={"type": "array", "items": WorkExperienceEntry.model_json_schema()},
        )
        llm_work = response["message"]["content"]
        try:
            work_experience = [
                WorkExperienceEntry.model_validate_json(item)
                for item in json.loads(llm_work)
            ]
            work_experience = [w.model_dump() for w in work_experience]
        except Exception as e:
            logging.error(f"Error parsing work experience with Pydantic: {e}")
        logging.info(f"Ollama work experience: {work_experience}")
    except Exception as e:
        logging.error(f"Ollama work experience error: {e}")
    return work_experience


async def ollama_extract_projects(text: str):
    from models.resume import ProjectEntry

    projects = []
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract the projects section from the resume text. "
                    "Return a list of objects with name and bullets."
                ),
            },
            {"role": "user", "content": text},
        ]
        logging.info("Calling Ollama for projects...")
        response = await ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format={"type": "array", "items": ProjectEntry.model_json_schema()},
        )
        llm_projects = response["message"]["content"]
        try:
            projects = [
                ProjectEntry.model_validate_json(item)
                for item in json.loads(llm_projects)
            ]
            projects = [p.model_dump() for p in projects]
        except Exception as e:
            logging.error(f"Error parsing projects with Pydantic: {e}")
        logging.info(f"Ollama projects: {projects}")
    except Exception as e:
        logging.error(f"Ollama projects error: {e}")
    return projects


async def ollama_extract_skills(text: str):
    skills = []
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract the skills section from the resume text. "
                    "Return a list of strings, each string being a skill."
                ),
            },
            {"role": "user", "content": text},
        ]
        logging.info("Calling Ollama for skills...")
        response = await ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format={"type": "array", "items": {"type": "string"}},
        )
        llm_skills = response["message"]["content"]
        try:
            skills = json.loads(llm_skills)
        except Exception as e:
            logging.error(f"Error parsing skills: {e}")
        logging.info(f"Ollama skills: {skills}")
    except Exception as e:
        logging.error(f"Ollama skills error: {e}")
    return skills
