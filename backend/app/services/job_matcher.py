"""
Enhanced JobMatcher service for advanced job description analysis and resume matching.

This service provides comprehensive job description parsing, skill extraction,
industry-specific keyword identification, and resume-to-job matching capabilities.
"""

import re
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
import logging

from models.job_analysis import (
    JobDescription,
    JobAnalysis,
    SkillRequirement,
    ResumeJobMatch,
    JobMatchRecommendation,
    JobComparisonResult,
)
from models.resume import ResumeDocument, ResumeSections
from services.llm_provider import LLMProviderBase

logger = logging.getLogger(__name__)


class JobMatcher:
    """
    Enhanced JobMatcher service for comprehensive job description analysis and resume matching.

    This service provides:
    - Advanced job description parsing and analysis
    - Comprehensive skill extraction and categorization
    - Industry-specific keyword identification
    - Resume-to-job matching with detailed scoring
    - Recommendation generation for resume improvements
    """

    def __init__(self, llm_provider: LLMProviderBase):
        self.llm_provider = llm_provider
        self.skill_categories = {
            "technical": [
                "programming",
                "software",
                "development",
                "coding",
                "algorithm",
                "database",
                "sql",
                "nosql",
                "api",
                "framework",
                "library",
                "cloud",
                "aws",
                "azure",
                "gcp",
                "docker",
                "kubernetes",
                "machine learning",
                "ai",
                "data science",
                "analytics",
                "web development",
                "mobile development",
                "devops",
                "ci/cd",
            ],
            "soft": [
                "communication",
                "leadership",
                "teamwork",
                "collaboration",
                "problem solving",
                "critical thinking",
                "creativity",
                "adaptability",
                "time management",
                "project management",
                "mentoring",
                "coaching",
            ],
            "language": [
                "english",
                "spanish",
                "french",
                "german",
                "chinese",
                "japanese",
                "korean",
                "portuguese",
                "italian",
                "russian",
                "arabic",
                "hindi",
            ],
            "certification": [
                "certified",
                "certification",
                "license",
                "accredited",
                "chartered",
                "professional",
                "associate",
                "expert",
                "specialist",
                "master",
            ],
            "tool": [
                "excel",
                "powerpoint",
                "word",
                "outlook",
                "slack",
                "jira",
                "confluence",
                "git",
                "github",
                "gitlab",
                "jenkins",
                "terraform",
            ],
        }

        self.industry_keywords = {
            "technology": [
                "software",
                "tech",
                "digital",
                "innovation",
                "startup",
                "saas",
                "platform",
                "scalable",
                "agile",
                "scrum",
                "microservices",
            ],
            "finance": [
                "financial",
                "banking",
                "investment",
                "trading",
                "risk management",
                "compliance",
                "regulatory",
                "audit",
                "fintech",
                "blockchain",
            ],
            "healthcare": [
                "medical",
                "healthcare",
                "clinical",
                "patient",
                "treatment",
                "diagnosis",
                "pharmaceutical",
                "biotech",
                "fda",
                "hipaa",
            ],
            "consulting": [
                "consulting",
                "advisory",
                "strategy",
                "transformation",
                "optimization",
                "implementation",
                "client",
                "stakeholder",
                "business process",
            ],
            "marketing": [
                "marketing",
                "brand",
                "campaign",
                "digital marketing",
                "seo",
                "sem",
                "social media",
                "content",
                "analytics",
                "conversion",
                "roi",
            ],
            "sales": [
                "sales",
                "revenue",
                "quota",
                "pipeline",
                "crm",
                "lead generation",
                "customer acquisition",
                "account management",
                "negotiation",
            ],
        }

    async def analyze_job_description(self, job_desc: str) -> JobAnalysis:
        """
        Analyze a job description and extract comprehensive information.

        Args:
            job_desc: Raw job description text

        Returns:
            JobAnalysis object with extracted information
        """
        start_time = datetime.utcnow()

        try:
            # Create JobDescription object
            job_description = JobDescription(raw_text=job_desc)

            # Extract basic information
            job_title = await self._extract_job_title(job_desc)
            company = await self._extract_company_name(job_desc)
            industry = await self._identify_industry(job_desc)

            # Extract skills and requirements
            required_skills = await self._extract_skills(
                job_desc, importance="required"
            )
            preferred_skills = await self._extract_skills(
                job_desc, importance="preferred"
            )

            # Categorize skills
            technical_skills = self._categorize_skills(
                required_skills + preferred_skills, "technical"
            )
            soft_skills = self._categorize_skills(
                required_skills + preferred_skills, "soft"
            )
            certifications = self._categorize_skills(
                required_skills + preferred_skills, "certification"
            )
            tools_technologies = self._categorize_skills(
                required_skills + preferred_skills, "tool"
            )

            # Extract experience requirements
            min_years, max_years = await self._extract_experience_requirements(job_desc)
            education_requirements = await self._extract_education_requirements(
                job_desc
            )

            # Extract job details
            key_responsibilities = await self._extract_responsibilities(job_desc)
            company_values = await self._extract_company_values(job_desc)
            benefits = await self._extract_benefits(job_desc)

            # Extract keywords and phrases
            industry_keywords = self._extract_industry_keywords(job_desc, industry)
            action_verbs = self._extract_action_verbs(job_desc)
            buzzwords = self._extract_buzzwords(job_desc)

            # Calculate confidence score
            confidence_score = self._calculate_analysis_confidence(
                job_title, required_skills, key_responsibilities
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return JobAnalysis(
                job_description_id=job_description.id,
                job_title=job_title,
                company=company,
                industry=industry,
                required_skills=required_skills,
                preferred_skills=preferred_skills,
                technical_skills=technical_skills,
                soft_skills=soft_skills,
                certifications=certifications,
                tools_technologies=tools_technologies,
                min_years_experience=min_years,
                max_years_experience=max_years,
                education_requirements=education_requirements,
                key_responsibilities=key_responsibilities,
                company_values=company_values,
                benefits=benefits,
                industry_keywords=industry_keywords,
                action_verbs=action_verbs,
                buzzwords=buzzwords,
                confidence_score=confidence_score,
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            logger.error(f"Error analyzing job description: {str(e)}")
            raise

    async def match_resume_to_job(
        self, resume: ResumeDocument, job_analysis: JobAnalysis
    ) -> ResumeJobMatch:
        """
        Match a resume against a job analysis and generate detailed scoring.

        Args:
            resume: Resume document to analyze
            job_analysis: Job analysis to match against

        Returns:
            ResumeJobMatch with detailed scoring and recommendations
        """
        try:
            # Calculate section-specific scores
            section_scores = await self._calculate_section_scores(
                resume.sections, job_analysis
            )

            # Analyze skill matching
            skill_match_result = await self._analyze_skill_matching(
                resume.sections, job_analysis
            )

            # Check experience matching
            experience_match, experience_gap = await self._check_experience_match(
                resume.sections, job_analysis
            )

            # Calculate keyword matching
            keyword_score, missing_keywords = await self._calculate_keyword_matching(
                resume.sections, job_analysis
            )

            # Calculate overall match score
            overall_score = self._calculate_overall_match_score(
                section_scores,
                skill_match_result["percentage"],
                keyword_score,
                experience_match,
            )

            # Determine recommendation level
            recommendation = self._determine_recommendation_level(overall_score)

            return ResumeJobMatch(
                resume_id=resume.id,
                job_analysis_id=job_analysis.id,
                overall_match_score=overall_score,
                recommendation=recommendation,
                section_scores=section_scores,
                matching_skills=skill_match_result["matching"],
                missing_required_skills=skill_match_result["missing_required"],
                missing_preferred_skills=skill_match_result["missing_preferred"],
                skill_match_percentage=skill_match_result["percentage"],
                experience_match=experience_match,
                experience_gap_years=experience_gap,
                keyword_match_score=keyword_score,
                missing_keywords=missing_keywords,
            )

        except Exception as e:
            logger.error(f"Error matching resume to job: {str(e)}")
            raise

    async def generate_section_recommendations(
        self, section: str, job_analysis: JobAnalysis, current_content: Dict[str, Any]
    ) -> List[JobMatchRecommendation]:
        """
        Generate specific recommendations for improving a resume section based on job analysis.

        Args:
            section: Resume section name
            job_analysis: Job analysis to base recommendations on
            current_content: Current content of the resume section

        Returns:
            List of specific recommendations
        """
        try:
            recommendations = []

            if section == "work_experience":
                recommendations.extend(
                    await self._generate_experience_recommendations(
                        job_analysis, current_content
                    )
                )
            elif section == "skills":
                recommendations.extend(
                    await self._generate_skills_recommendations(
                        job_analysis, current_content
                    )
                )
            elif section == "projects":
                recommendations.extend(
                    await self._generate_projects_recommendations(
                        job_analysis, current_content
                    )
                )
            elif section == "education":
                recommendations.extend(
                    await self._generate_education_recommendations(
                        job_analysis, current_content
                    )
                )
            elif section == "personal_details":
                recommendations.extend(
                    await self._generate_summary_recommendations(
                        job_analysis, current_content
                    )
                )

            # Sort by priority and expected impact
            recommendations.sort(
                key=lambda x: (
                    {"high": 3, "medium": 2, "low": 1}[x.priority],
                    x.expected_impact,
                ),
                reverse=True,
            )

            return recommendations

        except Exception as e:
            logger.error(
                f"Error generating recommendations for section {section}: {str(e)}"
            )
            raise

    async def calculate_match_score(
        self, resume: ResumeDocument, job_analysis: JobAnalysis
    ) -> float:
        """
        Calculate a simple match score between resume and job.

        Args:
            resume: Resume document
            job_analysis: Job analysis

        Returns:
            Match score between 0.0 and 1.0
        """
        try:
            match_result = await self.match_resume_to_job(resume, job_analysis)
            return match_result.overall_match_score
        except Exception as e:
            logger.error(f"Error calculating match score: {str(e)}")
            return 0.0

    # Private helper methods for job description analysis

    async def _extract_job_title(self, job_desc: str) -> str:
        """Extract job title from job description using LLM."""
        prompt = f"""
        Extract the job title from this job description. Return only the job title, nothing else.
        
        Job Description:
        {job_desc[:1000]}
        """

        try:
            # Use LLM to extract job title
            response = await self._call_llm_for_extraction(prompt)
            return response.strip() if response else "Unknown Position"
        except Exception:
            # Fallback to regex pattern matching
            patterns = [
                r"(?i)job title[:\s]+([^\n\r]+)",
                r"(?i)position[:\s]+([^\n\r]+)",
                r"(?i)role[:\s]+([^\n\r]+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, job_desc)
                if match:
                    return match.group(1).strip()

            return "Unknown Position"

    async def _extract_company_name(self, job_desc: str) -> Optional[str]:
        """Extract company name from job description."""
        patterns = [
            r"(?i)company[:\s]+([^\n\r]+)",
            r"(?i)employer[:\s]+([^\n\r]+)",
            r"(?i)organization[:\s]+([^\n\r]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, job_desc)
            if match:
                return match.group(1).strip()

        return None

    async def _identify_industry(self, job_desc: str) -> Optional[str]:
        """Identify industry based on job description content."""
        job_desc_lower = job_desc.lower()

        industry_scores = {}
        for industry, keywords in self.industry_keywords.items():
            score = sum(1 for keyword in keywords if keyword in job_desc_lower)
            if score > 0:
                industry_scores[industry] = score

        if industry_scores:
            return max(industry_scores, key=industry_scores.get)

        return None

    async def _extract_skills(
        self, job_desc: str, importance: str
    ) -> List[SkillRequirement]:
        """Extract skills from job description with specified importance level."""
        prompt = f"""
        Extract {importance} skills from this job description. For each skill, identify:
        1. Skill name
        2. Category (technical, soft, language, certification, tool)
        3. Proficiency level if mentioned (beginner, intermediate, advanced, expert)
        4. Years of experience if specified
        5. Context where it's mentioned
        
        Return as JSON array with objects containing: name, category, proficiency_level, years_experience, context
        
        Job Description:
        {job_desc}
        """

        try:
            response = await self._call_llm_for_extraction(prompt)
            skills_data = json.loads(response) if response else []

            skills = []
            for skill_data in skills_data:
                skill = SkillRequirement(
                    name=skill_data.get("name", ""),
                    category=skill_data.get("category", "technical"),
                    importance=importance,
                    proficiency_level=skill_data.get("proficiency_level"),
                    years_experience=skill_data.get("years_experience"),
                    context=skill_data.get("context"),
                )
                skills.append(skill)

            return skills

        except Exception as e:
            logger.warning(f"LLM skill extraction failed, using fallback: {str(e)}")
            return self._extract_skills_fallback(job_desc, importance)

    def _extract_skills_fallback(
        self, job_desc: str, importance: str
    ) -> List[SkillRequirement]:
        """Fallback method for skill extraction using pattern matching."""
        skills = []
        job_desc_lower = job_desc.lower()

        # Look for common skill patterns
        for category, keywords in self.skill_categories.items():
            for keyword in keywords:
                if keyword in job_desc_lower:
                    skill = SkillRequirement(
                        name=keyword.title(), category=category, importance=importance
                    )
                    skills.append(skill)

        return skills

    def _categorize_skills(
        self, skills: List[SkillRequirement], category: str
    ) -> List[str]:
        """Extract skills of a specific category."""
        return [skill.name for skill in skills if skill.category == category]

    async def _extract_experience_requirements(
        self, job_desc: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """Extract minimum and maximum years of experience required."""
        # Pattern to match experience requirements
        patterns = [
            r"(\d+)[\+\-\s]*(?:to|-)?\s*(\d+)?\s*years?\s+(?:of\s+)?experience",
            r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
            r"minimum\s+(\d+)\s*years?",
            r"at least\s+(\d+)\s*years?",
        ]

        min_years = None
        max_years = None

        for pattern in patterns:
            matches = re.finditer(pattern, job_desc.lower())
            for match in matches:
                if match.group(2):  # Range format (e.g., "3-5 years")
                    min_years = int(match.group(1))
                    max_years = int(match.group(2))
                else:  # Single number format
                    min_years = int(match.group(1))
                break

        return min_years, max_years

    async def _extract_education_requirements(self, job_desc: str) -> List[str]:
        """Extract education requirements from job description."""
        education_keywords = [
            "bachelor",
            "master",
            "phd",
            "doctorate",
            "degree",
            "diploma",
            "certification",
            "associate",
            "graduate",
            "undergraduate",
        ]

        requirements = []
        job_desc_lower = job_desc.lower()

        for keyword in education_keywords:
            if keyword in job_desc_lower:
                # Extract the sentence containing the education requirement
                sentences = job_desc.split(".")
                for sentence in sentences:
                    if keyword in sentence.lower():
                        requirements.append(sentence.strip())
                        break

        return list(set(requirements))  # Remove duplicates

    async def _extract_responsibilities(self, job_desc: str) -> List[str]:
        """Extract key responsibilities from job description."""
        prompt = f"""
        Extract the key responsibilities and duties from this job description.
        Return as a JSON array of strings, each representing a responsibility.
        
        Job Description:
        {job_desc}
        """

        try:
            response = await self._call_llm_for_extraction(prompt)
            responsibilities = json.loads(response) if response else []
            return responsibilities if isinstance(responsibilities, list) else []
        except Exception:
            # Fallback to pattern matching
            return self._extract_responsibilities_fallback(job_desc)

    def _extract_responsibilities_fallback(self, job_desc: str) -> List[str]:
        """Fallback method for extracting responsibilities."""
        # Look for bullet points or numbered lists
        patterns = [
            r"[•\-\*]\s*([^\n\r]+)",
            r"\d+\.\s*([^\n\r]+)",
        ]

        responsibilities = []
        for pattern in patterns:
            matches = re.findall(pattern, job_desc)
            responsibilities.extend([match.strip() for match in matches])

        return responsibilities[:10]  # Limit to top 10

    async def _extract_company_values(self, job_desc: str) -> List[str]:
        """Extract company values and culture information."""
        value_keywords = [
            "values",
            "culture",
            "mission",
            "vision",
            "principles",
            "commitment",
            "dedication",
            "integrity",
            "innovation",
        ]

        values = []
        job_desc_lower = job_desc.lower()

        for keyword in value_keywords:
            if keyword in job_desc_lower:
                # Extract sentences containing value keywords
                sentences = job_desc.split(".")
                for sentence in sentences:
                    if keyword in sentence.lower() and len(sentence.strip()) > 20:
                        values.append(sentence.strip())

        return list(set(values))[:5]  # Limit to top 5

    async def _extract_benefits(self, job_desc: str) -> List[str]:
        """Extract benefits and perks from job description."""
        benefit_keywords = [
            "benefits",
            "perks",
            "compensation",
            "salary",
            "insurance",
            "health",
            "dental",
            "vision",
            "401k",
            "retirement",
            "vacation",
            "pto",
            "flexible",
            "remote",
            "work from home",
        ]

        benefits = []
        job_desc_lower = job_desc.lower()

        for keyword in benefit_keywords:
            if keyword in job_desc_lower:
                # Extract sentences containing benefit keywords
                sentences = job_desc.split(".")
                for sentence in sentences:
                    if keyword in sentence.lower() and len(sentence.strip()) > 15:
                        benefits.append(sentence.strip())

        return list(set(benefits))[:8]  # Limit to top 8

    def _extract_industry_keywords(
        self, job_desc: str, industry: Optional[str]
    ) -> List[str]:
        """Extract industry-specific keywords."""
        if not industry or industry not in self.industry_keywords:
            return []

        keywords = []
        job_desc_lower = job_desc.lower()

        for keyword in self.industry_keywords[industry]:
            if keyword in job_desc_lower:
                keywords.append(keyword)

        return keywords

    def _extract_action_verbs(self, job_desc: str) -> List[str]:
        """Extract action verbs commonly used in job descriptions."""
        action_verbs = [
            "develop",
            "create",
            "manage",
            "lead",
            "implement",
            "design",
            "analyze",
            "optimize",
            "collaborate",
            "coordinate",
            "execute",
            "maintain",
            "support",
            "troubleshoot",
            "monitor",
            "evaluate",
        ]

        found_verbs = []
        job_desc_lower = job_desc.lower()

        for verb in action_verbs:
            if verb in job_desc_lower:
                found_verbs.append(verb)

        return found_verbs

    def _extract_buzzwords(self, job_desc: str) -> List[str]:
        """Extract common industry buzzwords."""
        buzzwords = [
            "innovative",
            "dynamic",
            "fast-paced",
            "cutting-edge",
            "scalable",
            "agile",
            "collaborative",
            "results-driven",
            "customer-focused",
            "data-driven",
            "strategic",
            "cross-functional",
            "end-to-end",
        ]

        found_buzzwords = []
        job_desc_lower = job_desc.lower()

        for buzzword in buzzwords:
            if buzzword in job_desc_lower:
                found_buzzwords.append(buzzword)

        return found_buzzwords

    def _calculate_analysis_confidence(
        self,
        job_title: str,
        required_skills: List[SkillRequirement],
        responsibilities: List[str],
    ) -> float:
        """Calculate confidence score for the job analysis."""
        score = 0.0

        # Job title extracted
        if job_title and job_title != "Unknown Position":
            score += 0.3

        # Skills extracted
        if required_skills:
            score += min(0.4, len(required_skills) * 0.05)

        # Responsibilities extracted
        if responsibilities:
            score += min(0.3, len(responsibilities) * 0.03)

        return min(1.0, score)

    # Private helper methods for resume matching

    async def _calculate_section_scores(
        self, resume_sections: ResumeSections, job_analysis: JobAnalysis
    ) -> Dict[str, float]:
        """Calculate match scores for each resume section."""
        scores = {}

        # Work experience score
        scores["work_experience"] = await self._score_work_experience(
            resume_sections.work_experience, job_analysis
        )

        # Skills score
        scores["skills"] = await self._score_skills_section(
            resume_sections.skills, job_analysis
        )

        # Projects score
        scores["projects"] = await self._score_projects_section(
            resume_sections.projects, job_analysis
        )

        # Education score
        scores["education"] = await self._score_education_section(
            resume_sections.education, job_analysis
        )

        # Summary/objective score
        scores["summary"] = await self._score_summary_section(
            resume_sections.personal_details, job_analysis
        )

        return scores

    async def _score_work_experience(
        self, work_experience: List, job_analysis: JobAnalysis
    ) -> float:
        """Score work experience section against job requirements."""
        if not work_experience:
            return 0.0

        total_score = 0.0
        max_score = 0.0

        for exp in work_experience:
            exp_score = 0.0

            # Check for relevant technologies
            exp_technologies = [tech.lower() for tech in exp.technologies]
            job_tech_skills = [
                skill.name.lower()
                for skill in job_analysis.required_skills
                if skill.category == "technical"
            ]

            tech_matches = len(set(exp_technologies) & set(job_tech_skills))
            exp_score += tech_matches * 0.2

            # Check for relevant keywords in achievements
            if exp.achievements:
                achievement_text = " ".join(exp.achievements).lower()
                keyword_matches = sum(
                    1
                    for keyword in job_analysis.industry_keywords
                    if keyword in achievement_text
                )
                exp_score += keyword_matches * 0.1

            total_score += exp_score
            max_score += 1.0

        return min(1.0, total_score / max_score) if max_score > 0 else 0.0

    async def _score_skills_section(
        self, skills: List, job_analysis: JobAnalysis
    ) -> float:
        """Score skills section against job requirements."""
        if not skills:
            return 0.0

        resume_skills = set()
        for skill_category in skills:
            resume_skills.update([skill.lower() for skill in skill_category.skills])

        required_skills = set(
            [skill.name.lower() for skill in job_analysis.required_skills]
        )
        preferred_skills = set(
            [skill.name.lower() for skill in job_analysis.preferred_skills]
        )

        required_matches = len(resume_skills & required_skills)
        preferred_matches = len(resume_skills & preferred_skills)

        total_required = len(required_skills)
        total_preferred = len(preferred_skills)

        score = 0.0
        if total_required > 0:
            score += (required_matches / total_required) * 0.7
        if total_preferred > 0:
            score += (preferred_matches / total_preferred) * 0.3

        return min(1.0, score)

    async def _score_projects_section(
        self, projects: List, job_analysis: JobAnalysis
    ) -> float:
        """Score projects section against job requirements."""
        if not projects:
            return 0.0

        total_score = 0.0

        for project in projects:
            project_score = 0.0

            # Check technologies used
            project_technologies = [tech.lower() for tech in project.technologies]
            job_tech_skills = [
                skill.name.lower()
                for skill in job_analysis.required_skills
                if skill.category == "technical"
            ]

            tech_matches = len(set(project_technologies) & set(job_tech_skills))
            project_score += tech_matches * 0.3

            # Check project description for relevant keywords
            project_text = f"{project.name} {project.summary or ''} {' '.join(project.bullets)}".lower()
            keyword_matches = sum(
                1
                for keyword in job_analysis.industry_keywords
                if keyword in project_text
            )
            project_score += keyword_matches * 0.1

            total_score += min(1.0, project_score)

        return min(1.0, total_score / len(projects))

    async def _score_education_section(
        self, education: List, job_analysis: JobAnalysis
    ) -> float:
        """Score education section against job requirements."""
        if not education or not job_analysis.education_requirements:
            return 0.5  # Neutral score if no education requirements

        education_text = " ".join(
            [f"{edu.degree} {edu.university}" for edu in education]
        ).lower()

        matches = 0
        for requirement in job_analysis.education_requirements:
            if any(
                keyword in education_text for keyword in requirement.lower().split()
            ):
                matches += 1

        return min(1.0, matches / len(job_analysis.education_requirements))

    async def _score_summary_section(
        self, personal_details, job_analysis: JobAnalysis
    ) -> float:
        """Score summary/objective section against job requirements."""
        summary_text = ""
        if personal_details.summary:
            summary_text += personal_details.summary.lower()
        if personal_details.objective:
            summary_text += " " + personal_details.objective.lower()

        if not summary_text:
            return 0.0

        # Check for job-relevant keywords
        keyword_matches = sum(
            1 for keyword in job_analysis.industry_keywords if keyword in summary_text
        )

        # Check for required skills mentioned
        skill_matches = sum(
            1
            for skill in job_analysis.required_skills
            if skill.name.lower() in summary_text
        )

        total_keywords = len(job_analysis.industry_keywords)
        total_skills = len(job_analysis.required_skills)

        score = 0.0
        if total_keywords > 0:
            score += (keyword_matches / total_keywords) * 0.5
        if total_skills > 0:
            score += (skill_matches / total_skills) * 0.5

        return min(1.0, score)

    async def _analyze_skill_matching(
        self, resume_sections: ResumeSections, job_analysis: JobAnalysis
    ) -> Dict[str, Any]:
        """Analyze skill matching between resume and job."""
        # Extract all resume skills
        resume_skills = set()
        for skill_category in resume_sections.skills:
            resume_skills.update([skill.lower() for skill in skill_category.skills])

        # Extract job skills
        required_skills = set(
            [skill.name.lower() for skill in job_analysis.required_skills]
        )
        preferred_skills = set(
            [skill.name.lower() for skill in job_analysis.preferred_skills]
        )

        # Calculate matches
        matching_skills = list(resume_skills & (required_skills | preferred_skills))
        missing_required = list(required_skills - resume_skills)
        missing_preferred = list(preferred_skills - resume_skills)

        # Calculate percentage
        total_job_skills = len(required_skills | preferred_skills)
        match_percentage = (
            len(matching_skills) / total_job_skills if total_job_skills > 0 else 0.0
        )

        return {
            "matching": matching_skills,
            "missing_required": missing_required,
            "missing_preferred": missing_preferred,
            "percentage": match_percentage,
        }

    async def _check_experience_match(
        self, resume_sections: ResumeSections, job_analysis: JobAnalysis
    ) -> Tuple[bool, int]:
        """Check if resume experience matches job requirements."""
        if not job_analysis.min_years_experience:
            return True, 0

        # Calculate total years of experience from resume
        total_experience = 0
        for exp in resume_sections.work_experience:
            # Simple calculation - could be enhanced with date parsing
            if exp.from_date and exp.to_date:
                # Placeholder calculation - in real implementation, parse dates properly
                total_experience += 2  # Assume 2 years per job for now

        experience_match = total_experience >= job_analysis.min_years_experience
        experience_gap = max(0, job_analysis.min_years_experience - total_experience)

        return experience_match, experience_gap

    async def _calculate_keyword_matching(
        self, resume_sections: ResumeSections, job_analysis: JobAnalysis
    ) -> Tuple[float, List[str]]:
        """Calculate keyword matching score."""
        # Extract all text from resume
        resume_text = self._extract_all_resume_text(resume_sections).lower()

        # Check for industry keywords
        total_keywords = len(job_analysis.industry_keywords)
        if total_keywords == 0:
            return 1.0, []

        matching_keywords = [
            kw for kw in job_analysis.industry_keywords if kw in resume_text
        ]
        missing_keywords = [
            kw for kw in job_analysis.industry_keywords if kw not in resume_text
        ]

        score = len(matching_keywords) / total_keywords

        return score, missing_keywords

    def _extract_all_resume_text(self, resume_sections: ResumeSections) -> str:
        """Extract all text content from resume sections."""
        text_parts = []

        # Personal details
        if resume_sections.personal_details.summary:
            text_parts.append(resume_sections.personal_details.summary)
        if resume_sections.personal_details.objective:
            text_parts.append(resume_sections.personal_details.objective)

        # Work experience
        for exp in resume_sections.work_experience:
            text_parts.append(f"{exp.title} {exp.company}")
            if exp.summary:
                text_parts.append(exp.summary)
            text_parts.extend(exp.achievements)
            text_parts.extend(exp.technologies)

        # Projects
        for project in resume_sections.projects:
            text_parts.append(f"{project.name} {project.summary or ''}")
            text_parts.extend(project.bullets)
            text_parts.extend(project.technologies)

        # Skills
        for skill_category in resume_sections.skills:
            text_parts.extend(skill_category.skills)

        # Education
        for edu in resume_sections.education:
            text_parts.append(f"{edu.degree} {edu.university}")

        return " ".join(text_parts)

    def _calculate_overall_match_score(
        self,
        section_scores: Dict[str, float],
        skill_percentage: float,
        keyword_score: float,
        experience_match: bool,
    ) -> float:
        """Calculate overall match score with weighted components."""
        weights = {
            "skills": 0.3,
            "work_experience": 0.25,
            "projects": 0.15,
            "education": 0.1,
            "summary": 0.1,
            "keyword_match": 0.1,
        }

        score = 0.0

        # Section scores
        for section, weight in weights.items():
            if section == "keyword_match":
                score += keyword_score * weight
            else:
                score += section_scores.get(section, 0.0) * weight

        # Experience penalty
        if not experience_match:
            score *= 0.8

        return min(1.0, score)

    def _determine_recommendation_level(self, overall_score: float) -> str:
        """Determine recommendation level based on overall score."""
        if overall_score >= 0.8:
            return "strong_match"
        elif overall_score >= 0.6:
            return "good_match"
        elif overall_score >= 0.4:
            return "moderate_match"
        else:
            return "weak_match"

    # Recommendation generation methods

    async def _generate_experience_recommendations(
        self, job_analysis: JobAnalysis, current_content: Dict[str, Any]
    ) -> List[JobMatchRecommendation]:
        """Generate recommendations for work experience section."""
        recommendations = []

        # Check for missing technical skills in experience
        current_technologies = set()
        for exp in current_content.get("work_experience", []):
            current_technologies.update(
                [tech.lower() for tech in exp.get("technologies", [])]
            )

        required_tech_skills = [
            skill.name.lower()
            for skill in job_analysis.required_skills
            if skill.category == "technical"
        ]
        missing_tech = set(required_tech_skills) - current_technologies

        for tech in list(missing_tech)[:3]:  # Top 3 missing technologies
            recommendations.append(
                JobMatchRecommendation(
                    match_id="",  # Will be set by caller
                    section="work_experience",
                    type="add_skill",
                    priority="high",
                    title=f"Add {tech.title()} Experience",
                    description=f"Highlight experience with {tech.title()} in your work history",
                    specific_action=f"Add {tech.title()} to technologies used in relevant positions",
                    expected_impact=0.15,
                    difficulty="easy",
                    estimated_time_minutes=10,
                )
            )

        return recommendations

    async def _generate_skills_recommendations(
        self, job_analysis: JobAnalysis, current_content: Dict[str, Any]
    ) -> List[JobMatchRecommendation]:
        """Generate recommendations for skills section."""
        recommendations = []

        # Extract current skills
        current_skills = set()
        for skill_category in current_content.get("skills", []):
            current_skills.update(
                [skill.lower() for skill in skill_category.get("skills", [])]
            )

        # Find missing required skills
        required_skills = [skill.name.lower() for skill in job_analysis.required_skills]
        missing_skills = set(required_skills) - current_skills

        for skill in list(missing_skills)[:5]:  # Top 5 missing skills
            recommendations.append(
                JobMatchRecommendation(
                    match_id="",
                    section="skills",
                    type="add_skill",
                    priority="high",
                    title=f"Add {skill.title()} Skill",
                    description=f"Add {skill.title()} to your skills section as it's required for this role",
                    specific_action=f"Include {skill.title()} in the appropriate skill category",
                    expected_impact=0.2,
                    difficulty="easy",
                    estimated_time_minutes=5,
                )
            )

        return recommendations

    async def _generate_projects_recommendations(
        self, job_analysis: JobAnalysis, current_content: Dict[str, Any]
    ) -> List[JobMatchRecommendation]:
        """Generate recommendations for projects section."""
        recommendations = []

        # Check if projects use relevant technologies
        current_project_tech = set()
        for project in current_content.get("projects", []):
            current_project_tech.update(
                [tech.lower() for tech in project.get("technologies", [])]
            )

        required_tech = [
            skill.name.lower()
            for skill in job_analysis.required_skills
            if skill.category == "technical"
        ]
        missing_tech = set(required_tech) - current_project_tech

        if missing_tech:
            recommendations.append(
                JobMatchRecommendation(
                    match_id="",
                    section="projects",
                    type="add_skill",
                    priority="medium",
                    title="Add Relevant Technologies to Projects",
                    description="Include job-relevant technologies in your project descriptions",
                    specific_action=f"Add technologies like {', '.join(list(missing_tech)[:3])} to project descriptions",
                    expected_impact=0.1,
                    difficulty="medium",
                    estimated_time_minutes=15,
                )
            )

        return recommendations

    async def _generate_education_recommendations(
        self, job_analysis: JobAnalysis, current_content: Dict[str, Any]
    ) -> List[JobMatchRecommendation]:
        """Generate recommendations for education section."""
        recommendations = []

        if job_analysis.education_requirements and not current_content.get("education"):
            recommendations.append(
                JobMatchRecommendation(
                    match_id="",
                    section="education",
                    type="add_experience",
                    priority="medium",
                    title="Add Education Information",
                    description="Include your educational background as it's mentioned in job requirements",
                    specific_action="Add your degree, university, and graduation year",
                    expected_impact=0.1,
                    difficulty="easy",
                    estimated_time_minutes=10,
                )
            )

        return recommendations

    async def _generate_summary_recommendations(
        self, job_analysis: JobAnalysis, current_content: Dict[str, Any]
    ) -> List[JobMatchRecommendation]:
        """Generate recommendations for summary/objective section."""
        recommendations = []

        personal_details = current_content.get("personal_details", {})
        summary = personal_details.get("summary", "")

        if not summary:
            recommendations.append(
                JobMatchRecommendation(
                    match_id="",
                    section="personal_details",
                    type="add_experience",
                    priority="high",
                    title="Add Professional Summary",
                    description="Add a professional summary that highlights your relevant experience",
                    specific_action="Write a 2-3 sentence summary focusing on skills relevant to this role",
                    expected_impact=0.15,
                    difficulty="medium",
                    estimated_time_minutes=20,
                )
            )
        else:
            # Check if summary includes job-relevant keywords
            summary_lower = summary.lower()
            missing_keywords = [
                kw
                for kw in job_analysis.industry_keywords[:5]
                if kw not in summary_lower
            ]

            if missing_keywords:
                recommendations.append(
                    JobMatchRecommendation(
                        match_id="",
                        section="personal_details",
                        type="add_keyword",
                        priority="medium",
                        title="Optimize Summary Keywords",
                        description="Include more job-relevant keywords in your professional summary",
                        specific_action=f"Consider adding keywords like: {', '.join(missing_keywords[:3])}",
                        expected_impact=0.1,
                        difficulty="easy",
                        estimated_time_minutes=10,
                    )
                )

        return recommendations

    async def _call_llm_for_extraction(self, prompt: str) -> str:
        """Helper method to call LLM for text extraction tasks."""
        try:
            # This is a placeholder - implement based on your LLM provider interface
            # For now, return empty string to use fallback methods
            return ""
        except Exception as e:
            logger.warning(f"LLM call failed: {str(e)}")
            return ""
