import os
from app.configs.config import get_logger

logger = get_logger(__name__)
import json
import re
from typing import Dict
from app.models.resume import PersonalDetails, ResumeSections

# Use a custom client to allow custom host (API URL)


async def extract_personal_details(text: str, client, model) -> Dict:
    details = {"name": "", "contact": "", "linkedin": ""}
    try:
        messages = [
            {
                "role": "system",
                "content": "Extract the name, contact email, and LinkedIn URL from the following resume text. Return as JSON with keys: name, contact, linkedin.",
            },
            {"role": "user", "content": text},
        ]
        # Use LLM Python SDK
        logger.info(f"Calling LLM for personal details...")
        response = await client.chat(
            model=model,
            messages=messages,
            format=PersonalDetails.model_json_schema(),
        )
        llm_details = response["message"]["content"]
        logger.info(f"LLM response for personal details: {llm_details}")
        try:
            pd = PersonalDetails.model_validate_json(llm_details)
            details = pd.model_dump()
        except Exception as e:
            logger.error(f"Error parsing personal details with Pydantic: {e}")
        logger.info(f"LLM personal details: {details}")
    except Exception as e:
        logger.error(f"LLM personal details error: {e}")
    return details


async def extract_sections(text: str, client, model) -> Dict:
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
        logger.info(f"Calling LLM for sections...")
        response = await client.chat(
            model=model,
            messages=messages,
            format=ResumeSections.model_json_schema(),
        )
        llm_sections = response["message"]["content"]
        try:
            rs = ResumeSections.model_validate_json(llm_sections)
            sections = rs.model_dump()
        except Exception as e:
            logger.error(f"Error parsing sections with Pydantic: {e}")
        logger.info(f"LLM sections: {sections}")
    except Exception as e:
        logger.error(f"LLM sections error: {e}")
    return sections


async def extract_education(text: str, client, model):
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
        logger.info(f"Calling LLM for education...")
        response = await client.chat(
            model=model,
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
        logger.info(f"LLM education: {education}")
    except Exception as e:
        logger.error(f"LLM education error: {e}")
    return education


async def extract_work_experience(text: str, client, model):
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
        logger.info(f"Calling LLM for work experience...")
        response = await client.chat(
            model=model,
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
        logger.info(f"LLM work experience: {work_experience}")
    except Exception as e:
        logger.error(f"LLM work experience error: {e}")
    return work_experience


async def extract_projects(text: str, client, model):
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
        logger.info(f"Calling LLM for projects...")
        response = await client.chat(
            model=model,
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
        logger.info(f"LLM projects: {projects}")
    except Exception as e:
        logger.error(f"LLM projects error: {e}")
    return projects


async def extract_skills(text: str, client, model):
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
        logger.info(f"Calling LLM for skills...")
        response = await client.chat(
            model=model,
            messages=messages,
            format={"type": "array", "items": {"type": "string"}},
        )
        llm_skills = response["message"]["content"]
        try:
            skills = json.loads(llm_skills)
        except Exception as e:
            logger.error(f"Error parsing skills: {e}")
        logger.info(f"LLM skills: {skills}")
    except Exception as e:
        logger.error(f"LLM skills error: {e}")
    return skills
