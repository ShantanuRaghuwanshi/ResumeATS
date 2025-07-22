def optimize_resume_for_jd(parsed: dict, jd: str) -> dict:
    # Dummy logic: append JD keywords to skills
    import re

    jd_keywords = set(re.findall(r"\b\w+\b", jd.lower()))
    skills = parsed.get("skills", "")
    skills_set = set(re.findall(r"\b\w+\b", skills.lower()))
    new_skills = skills + "\n" + ", ".join(jd_keywords - skills_set)
    parsed["skills"] = new_skills
    # In production, use LLMs or NLP to match and rewrite experience, etc.
    return parsed
