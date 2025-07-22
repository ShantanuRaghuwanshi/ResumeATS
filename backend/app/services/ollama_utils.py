import os
import json
import re
from typing import Dict
from ollama import chat, AsyncClient
from app.models.resume import PersonalDetails, ResumeSections
from app.configs.config import get_logger

# Setup logger
logger = get_logger(__name__)


async def ollama_extract_personal_details(
    text: str, ollama_client: AsyncClient, OLLAMA_MODEL: str
) -> PersonalDetails:
    details = PersonalDetails(name="", linkedin="", email="")
    try:
        messages = [
            {
                "role": "system",
                "content": "Extract the name, contact email, and LinkedIn URL from the following resume text. Return as JSON with keys: name, contact, linkedin.",
            },
            {"role": "user", "content": text},
        ]
        # Use Ollama Python SDK
        logger.info("Calling Ollama for personal details...")
        response = await ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format=PersonalDetails.model_json_schema(),
        )
        llm_details = response["message"]["content"]
        logger.info(f"Ollama response for personal details: {llm_details}")
        try:
            details = PersonalDetails.model_construct(llm_details)
        except Exception as e:
            logger.error(f"Error parsing personal details with Pydantic: {e}")
        logger.info(f"Ollama personal details: {details.model_dump()}")
    except Exception as e:
        logger.error(f"Ollama personal details error: {e}")
    return details


async def ollama_extract_sections(
    text: str, ollama_client: AsyncClient, OLLAMA_MODEL: str
) -> ResumeSections:
    sections = ResumeSections(
        personal_details=PersonalDetails(name="", email="", linkedin=""),
        education=[],
        work_experience=[],
        projects=[],
        skills=[],
    )
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
        logger.info("Calling Ollama for sections...")
        response = await ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format=ResumeSections.model_json_schema(),
        )
        llm_sections = response["message"]["content"]
        try:
            sections = ResumeSections.model_construct(llm_sections)
        except Exception as e:
            logger.error(f"Error parsing sections with Pydantic: {e}")
        logger.info(f"Ollama sections: {sections}")
    except Exception as e:
        logger.error(f"Ollama sections error: {e}")
    return sections


async def ollama_extract_education(
    text: str, ollama_client: AsyncClient, OLLAMA_MODEL: str
):
    from app.models.resume import EducationEntry

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
        logger.info("Calling Ollama for education...")
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
            logger.error(f"Error parsing education with Pydantic: {e}")
        logger.info(f"Ollama education: {education}")
    except Exception as e:
        logger.error(f"Ollama education error: {e}")
    return education


async def ollama_extract_work_experience(
    text: str, ollama_client: AsyncClient, OLLAMA_MODEL: str
):
    from app.models.resume import WorkExperienceEntry

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
        logger.info("Calling Ollama for work experience...")
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
            logger.error(f"Error parsing work experience with Pydantic: {e}")
        logger.info(f"Ollama work experience: {work_experience}")
    except Exception as e:
        logger.error(f"Ollama work experience error: {e}")
    return work_experience


async def ollama_extract_projects(
    text: str, ollama_client: AsyncClient, OLLAMA_MODEL: str
):
    from app.models.resume import ProjectEntry

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
        logger.info("Calling Ollama for projects...")
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
            logger.error(f"Error parsing projects with Pydantic: {e}")
        logger.info(f"Ollama projects: {projects}")
    except Exception as e:
        logger.error(f"Ollama projects error: {e}")
    return projects


async def ollama_extract_skills(
    text: str, ollama_client: AsyncClient, OLLAMA_MODEL: str
):
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
        logger.info("Calling Ollama for skills...")
        response = await ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format={"type": "array", "items": {"type": "string"}},
        )
        llm_skills = response["message"]["content"]
        try:
            skills = json.loads(llm_skills)
        except Exception as e:
            logger.error(f"Error parsing skills: {e}")
        logger.info(f"Ollama skills: {skills}")
    except Exception as e:
        logger.error(f"Ollama skills error: {e}")
    return skills
