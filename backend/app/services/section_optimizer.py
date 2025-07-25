"""
Section Optimizer Service

Provides AI-powered optimization for individual resume sections with context awareness.
Handles section analysis, suggestion generation, and validation of modifications.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import re
from dataclasses import dataclass
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.optimization_request import (
    OptimizationRequest,
    OptimizationResult,
    SectionAnalysis,
    ImprovementMetrics,
    ValidationResult,
)
from models.conversation import Suggestion, ResumeContext
from models.resume import (
    ResumeSections,
    WorkExperienceEntry,
    EducationEntry,
    ProjectEntry,
)
from services.llm_provider import LLMProviderFactory
from database import get_database
from configs.config import get_logger

logger = get_logger(__name__)


@dataclass
class SectionOptimizationStrategy:
    """Strategy for optimizing a specific section type"""

    section_name: str
    key_elements: List[str]
    optimization_focus: List[str]
    common_issues: List[str]
    best_practices: List[str]
    ats_considerations: List[str]


class SectionOptimizer:
    """AI-powered section-specific resume optimization service"""

    def __init__(self):
        self.db = get_database()
        self.optimization_strategies = self._initialize_strategies()
        self.action_verbs = self._load_action_verbs()
        self.industry_keywords = self._load_industry_keywords()

    async def optimize_section(
        self,
        section_data: Dict[str, Any],
        context: ResumeContext,
        job_description: Optional[str] = None,
        optimization_type: str = "general",
        llm_provider: str = "openai",
        llm_config: Dict[str, Any] = None,
    ) -> OptimizationResult:
        """Optimize a specific resume section with AI assistance"""

        try:
            # Create optimization request
            request = OptimizationRequest(
                resume_id=context.resume_id,
                user_id=context.user_id,
                section=context.current_section,
                content=section_data,
                job_description=job_description,
                optimization_type=optimization_type,
            )

            # Store request
            self.db.create("optimization_requests", request.id, request.model_dump())

            # Analyze current section
            analysis = await self._analyze_section(
                section_data, context, job_description
            )

            # Generate optimized content
            optimized_content = await self._generate_optimized_content(
                section_data,
                analysis,
                context,
                job_description,
                llm_provider,
                llm_config,
            )

            # Generate suggestions
            suggestions = await self._generate_section_suggestions(
                section_data, optimized_content, analysis, context
            )

            # Calculate improvement metrics
            improvement_metrics = await self._calculate_improvement_metrics(
                section_data, optimized_content, context
            )

            # Create optimization result
            result = OptimizationResult(
                request_id=request.id,
                optimized_content=optimized_content,
                suggestions=[s.model_dump() for s in suggestions],
                improvement_score=improvement_metrics.improvement_percentage / 100,
                ats_score=improvement_metrics.ats_improvement,
                keyword_density=await self._calculate_keyword_density(
                    optimized_content
                ),
                readability_score=await self._calculate_readability_score(
                    optimized_content
                ),
                changes_summary=await self._generate_changes_summary(
                    section_data, optimized_content
                ),
                processing_time_seconds=0.0,  # Will be calculated
            )

            # Store result
            self.db.create("optimization_results", request.id, result.model_dump())

            logger.info(
                f"Optimized section {context.current_section} for user {context.user_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to optimize section: {e}")
            raise

    async def _generate_llm_content_suggestions(
        self,
        content: Dict,
        strategy: SectionOptimizationStrategy,
        context: ResumeContext,
        focus_areas: List[str] = None,
        llm_provider_instance=None,
    ) -> List[Suggestion]:
        """Generate content-based suggestions using LLM provider"""
        try:
            if not llm_provider_instance:
                return []

            # Convert content to string for LLM processing
            content_text = json.dumps(content) if isinstance(content, dict) else str(content)
            
            # Generate suggestions using LLM
            suggestions = await llm_provider_instance.generate_section_suggestions(
                section=context.current_section,
                content=content_text,
                context=context
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate LLM content suggestions: {e}")
            return []

    async def _generate_fallback_suggestions(
        self,
        section: str,
        content: Dict,
        strategy: SectionOptimizationStrategy,
        context: ResumeContext,
    ) -> List[Suggestion]:
        """Generate fallback suggestions when LLM provider is not available"""
        suggestions = []

        # Example content suggestions based on section
        if section == "work_experience":
            suggestions.append(
                Suggestion(
                    type="content",
                    title="Quantify Your Achievements",
                    description="Add specific numbers, percentages, and metrics to demonstrate your impact",
                    impact_score=0.9,
                    reasoning="Quantified achievements are more compelling and memorable",
                    section=section,
                    confidence=0.8,
                )
            )
            suggestions.append(
                Suggestion(
                    type="content",
                    title="Use Strong Action Verbs",
                    description="Start bullet points with powerful action verbs to show initiative",
                    impact_score=0.7,
                    reasoning="Action verbs make your contributions more dynamic and impactful",
                    section=section,
                    confidence=0.7,
                )
            )
        elif section == "skills":
            suggestions.append(
                Suggestion(
                    type="content",
                    title="Include Technical Skills",
                    description="Add relevant technical skills that match job requirements",
                    impact_score=0.8,
                    reasoning="Technical skills are often filtered by ATS systems",
                    section=section,
                    confidence=0.8,
                )
            )
        elif section == "education":
            suggestions.append(
                Suggestion(
                    type="content",
                    title="Include Relevant Coursework",
                    description="Add coursework relevant to your target position",
                    impact_score=0.6,
                    reasoning="Relevant coursework demonstrates specific knowledge areas",
                    section=section,
                    confidence=0.7,
                )
            )

        return suggestions

    async def suggest_improvements(
        self,
        section: str,
        content: Dict[str, Any],
        context: ResumeContext,
        focus_areas: List[str] = None,
        llm_provider: str = "ollama",
        llm_config: Dict[str, Any] = None,
    ) -> List[Suggestion]:
        """Generate improvement suggestions for a section using specified LLM provider"""

        try:
            # Get section strategy
            strategy = self.optimization_strategies.get(section)
            if not strategy:
                raise ValueError(
                    f"No optimization strategy found for section: {section}"
                )

            suggestions = []

            # Create LLM provider instance
            if llm_config is None:
                llm_config = {}
            
            try:
                llm_provider_instance = LLMProviderFactory.create(llm_provider, llm_config)
            except Exception as e:
                logger.warning(f"Failed to create LLM provider {llm_provider}: {e}. Falling back to hardcoded suggestions.")
                # Fallback to hardcoded suggestions if LLM provider fails
                return await self._generate_fallback_suggestions(section, content, strategy, context)

            # Content-based suggestions using LLM
            content_suggestions = await self._generate_llm_content_suggestions(
                content, strategy, context, focus_areas, llm_provider_instance
            )
            suggestions.extend(content_suggestions)

            # Structure-based suggestions
            structure_suggestions = await self._generate_structure_suggestions(
                content, strategy, context
            )
            suggestions.extend(structure_suggestions)

            # Keyword-based suggestions
            keyword_suggestions = await self._generate_keyword_suggestions(
                content, strategy, context
            )
            suggestions.extend(keyword_suggestions)

            # ATS-based suggestions
            ats_suggestions = await self._generate_ats_suggestions(
                content, strategy, context
            )
            suggestions.extend(ats_suggestions)

            # Sort by impact score
            suggestions.sort(key=lambda x: x.impact_score, reverse=True)

            return suggestions[:10]  # Return top 10 suggestions

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            raise

    async def validate_changes(
        self, original: Dict[str, Any], modified: Dict[str, Any], context: ResumeContext
    ) -> ValidationResult:
        """Validate changes made to a resume section"""

        try:
            errors = []
            warnings = []
            suggestions = []
            consistency_issues = []
            ats_issues = []
            formatting_issues = []

            # Basic validation
            if not modified:
                errors.append("Modified content cannot be empty")

            # Section-specific validation
            section = context.current_section

            if section == "personal_details":
                validation_result = await self._validate_personal_details(
                    original, modified
                )
            elif section == "work_experience":
                validation_result = await self._validate_work_experience(
                    original, modified
                )
            elif section == "education":
                validation_result = await self._validate_education(original, modified)
            elif section == "skills":
                validation_result = await self._validate_skills(original, modified)
            elif section == "projects":
                validation_result = await self._validate_projects(original, modified)
            else:
                validation_result = await self._validate_generic_section(
                    original, modified
                )

            errors.extend(validation_result.get("errors", []))
            warnings.extend(validation_result.get("warnings", []))
            suggestions.extend(validation_result.get("suggestions", []))

            # Cross-section consistency check
            consistency_check = await self._check_cross_section_consistency(
                modified, context
            )
            consistency_issues.extend(consistency_check)

            # ATS compatibility check
            ats_check = await self._check_ats_compatibility(modified, section)
            ats_issues.extend(ats_check)

            # Calculate overall quality score
            quality_score = await self._calculate_section_quality_score(
                modified, section, len(errors), len(warnings)
            )

            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions,
                consistency_issues=consistency_issues,
                ats_issues=ats_issues,
                formatting_issues=formatting_issues,
                overall_quality_score=quality_score,
            )

        except Exception as e:
            logger.error(f"Failed to validate changes: {e}")
            raise

    # Private helper methods

    def _initialize_strategies(self) -> Dict[str, SectionOptimizationStrategy]:
        """Initialize optimization strategies for different sections"""

        return {
            "personal_details": SectionOptimizationStrategy(
                section_name="Personal Details",
                key_elements=[
                    "name",
                    "email",
                    "phone",
                    "location",
                    "linkedin",
                    "summary",
                ],
                optimization_focus=[
                    "professional_summary",
                    "contact_info",
                    "personal_branding",
                ],
                common_issues=[
                    "missing_summary",
                    "unprofessional_email",
                    "incomplete_contact",
                ],
                best_practices=[
                    "clear_contact_info",
                    "compelling_summary",
                    "professional_links",
                ],
                ats_considerations=[
                    "standard_formatting",
                    "keyword_rich_summary",
                    "clear_structure",
                ],
            ),
            "work_experience": SectionOptimizationStrategy(
                section_name="Work Experience",
                key_elements=[
                    "title",
                    "company",
                    "dates",
                    "achievements",
                    "responsibilities",
                ],
                optimization_focus=[
                    "quantified_achievements",
                    "action_verbs",
                    "relevance",
                ],
                common_issues=[
                    "weak_verbs",
                    "no_metrics",
                    "job_duties_vs_achievements",
                ],
                best_practices=[
                    "start_with_action_verbs",
                    "quantify_impact",
                    "show_progression",
                ],
                ats_considerations=[
                    "standard_job_titles",
                    "keyword_optimization",
                    "date_formatting",
                ],
            ),
            "education": SectionOptimizationStrategy(
                section_name="Education",
                key_elements=[
                    "degree",
                    "institution",
                    "graduation_date",
                    "gpa",
                    "relevant_coursework",
                ],
                optimization_focus=[
                    "relevance",
                    "academic_achievements",
                    "certifications",
                ],
                common_issues=[
                    "irrelevant_details",
                    "missing_graduation_date",
                    "low_gpa_display",
                ],
                best_practices=[
                    "relevant_coursework",
                    "academic_honors",
                    "recent_first",
                ],
                ats_considerations=[
                    "standard_degree_names",
                    "clear_dates",
                    "institution_recognition",
                ],
            ),
            "skills": SectionOptimizationStrategy(
                section_name="Skills",
                key_elements=[
                    "technical_skills",
                    "soft_skills",
                    "proficiency_levels",
                    "categories",
                ],
                optimization_focus=[
                    "job_relevance",
                    "skill_categorization",
                    "proficiency_indication",
                ],
                common_issues=["skill_dumping", "outdated_skills", "no_categorization"],
                best_practices=[
                    "categorize_skills",
                    "prioritize_relevance",
                    "show_proficiency",
                ],
                ats_considerations=[
                    "keyword_matching",
                    "standard_skill_names",
                    "searchable_format",
                ],
            ),
            "projects": SectionOptimizationStrategy(
                section_name="Projects",
                key_elements=[
                    "project_name",
                    "description",
                    "technologies",
                    "outcomes",
                    "links",
                ],
                optimization_focus=["technical_depth", "business_impact", "innovation"],
                common_issues=[
                    "technical_jargon",
                    "no_business_context",
                    "missing_outcomes",
                ],
                best_practices=[
                    "explain_impact",
                    "highlight_technologies",
                    "provide_links",
                ],
                ats_considerations=[
                    "keyword_rich_descriptions",
                    "clear_structure",
                    "measurable_outcomes",
                ],
            ),
        }

    def _load_action_verbs(self) -> Dict[str, List[str]]:
        """Load action verbs categorized by impact level"""

        return {
            "leadership": [
                "led",
                "managed",
                "directed",
                "supervised",
                "coordinated",
                "orchestrated",
                "spearheaded",
                "championed",
                "guided",
                "mentored",
                "facilitated",
            ],
            "achievement": [
                "achieved",
                "accomplished",
                "delivered",
                "exceeded",
                "surpassed",
                "attained",
                "realized",
                "completed",
                "fulfilled",
                "secured",
                "obtained",
            ],
            "improvement": [
                "improved",
                "enhanced",
                "optimized",
                "streamlined",
                "upgraded",
                "modernized",
                "transformed",
                "revolutionized",
                "innovated",
                "automated",
                "accelerated",
            ],
            "creation": [
                "created",
                "developed",
                "designed",
                "built",
                "established",
                "founded",
                "launched",
                "initiated",
                "implemented",
                "constructed",
                "engineered",
            ],
            "analysis": [
                "analyzed",
                "evaluated",
                "assessed",
                "investigated",
                "researched",
                "examined",
                "studied",
                "reviewed",
                "audited",
                "diagnosed",
                "identified",
            ],
        }

    def _load_industry_keywords(self) -> Dict[str, List[str]]:
        """Load industry-specific keywords"""

        return {
            "technology": [
                "software development",
                "programming",
                "coding",
                "debugging",
                "testing",
                "deployment",
                "architecture",
                "scalability",
                "performance",
                "security",
                "cloud computing",
                "DevOps",
                "agile",
                "scrum",
                "CI/CD",
                "API",
                "database",
            ],
            "marketing": [
                "campaign management",
                "brand awareness",
                "lead generation",
                "conversion rate",
                "ROI",
                "analytics",
                "social media",
                "content marketing",
                "SEO",
                "SEM",
                "email marketing",
                "customer acquisition",
                "market research",
                "segmentation",
            ],
            "finance": [
                "financial analysis",
                "budgeting",
                "forecasting",
                "risk management",
                "compliance",
                "audit",
                "investment",
                "portfolio management",
                "valuation",
                "financial modeling",
                "reporting",
                "cost reduction",
                "revenue optimization",
            ],
            "sales": [
                "sales performance",
                "quota achievement",
                "client relationship",
                "lead conversion",
                "pipeline management",
                "territory management",
                "account management",
                "negotiation",
                "closing deals",
                "customer retention",
                "upselling",
                "cross-selling",
            ],
        }

    async def _analyze_section(
        self,
        section_data: Dict[str, Any],
        context: ResumeContext,
        job_description: Optional[str] = None,
    ) -> SectionAnalysis:
        """Analyze a resume section for strengths and weaknesses"""

        section = context.current_section
        strategy = self.optimization_strategies.get(section)

        # Basic analysis based on section type
        if section == "work_experience":
            analysis = await self._analyze_work_experience(section_data, strategy)
        elif section == "skills":
            analysis = await self._analyze_skills(
                section_data, strategy, job_description
            )
        elif section == "education":
            analysis = await self._analyze_education(section_data, strategy)
        elif section == "projects":
            analysis = await self._analyze_projects(section_data, strategy)
        else:
            analysis = await self._analyze_generic_section(section_data, strategy)

        return SectionAnalysis(
            section=section,
            current_content=section_data,
            strengths=analysis.get("strengths", []),
            weaknesses=analysis.get("weaknesses", []),
            missing_elements=analysis.get("missing_elements", []),
            keyword_gaps=analysis.get("keyword_gaps", []),
            improvement_opportunities=analysis.get("improvement_opportunities", []),
            ats_compatibility_score=analysis.get("ats_score", 0.7),
            content_quality_score=analysis.get("quality_score", 0.6),
            relevance_score=analysis.get("relevance_score", 0.8),
        )

    async def _analyze_work_experience(
        self, work_data: List[Dict[str, Any]], strategy: SectionOptimizationStrategy
    ) -> Dict[str, Any]:
        """Analyze work experience section"""

        strengths = []
        weaknesses = []
        missing_elements = []
        improvement_opportunities = []

        if not work_data:
            return {
                "strengths": [],
                "weaknesses": ["No work experience provided"],
                "missing_elements": ["Work experience entries"],
                "improvement_opportunities": ["Add work experience"],
                "ats_score": 0.0,
                "quality_score": 0.0,
                "relevance_score": 0.0,
            }

        for entry in work_data:
            # Check for quantified achievements
            description = entry.get("summary", "") + " ".join(
                entry.get("achievements", [])
            )
            if re.search(
                r"\d+%|\$\d+|\d+\+|increased|improved|reduced",
                description,
                re.IGNORECASE,
            ):
                strengths.append("Contains quantified achievements")
            else:
                weaknesses.append("Lacks quantified achievements")
                improvement_opportunities.append(
                    "Add specific metrics and numbers to achievements"
                )

            # Check for action verbs
            action_verb_found = False
            for category, verbs in self.action_verbs.items():
                if any(verb in description.lower() for verb in verbs):
                    action_verb_found = True
                    break

            if action_verb_found:
                strengths.append("Uses strong action verbs")
            else:
                weaknesses.append("Uses weak action verbs")
                improvement_opportunities.append(
                    "Start bullet points with strong action verbs"
                )

            # Check for required fields
            required_fields = ["title", "company", "from_date"]
            for field in required_fields:
                if not entry.get(field):
                    missing_elements.append(f"Missing {field}")

        # Calculate scores
        ats_score = min(1.0, len(strengths) / max(1, len(strengths) + len(weaknesses)))
        quality_score = max(0.0, 1.0 - (len(weaknesses) / max(1, len(work_data) * 3)))
        relevance_score = 0.8  # Default, would be calculated based on job description

        return {
            "strengths": list(set(strengths)),
            "weaknesses": list(set(weaknesses)),
            "missing_elements": missing_elements,
            "improvement_opportunities": list(set(improvement_opportunities)),
            "ats_score": ats_score,
            "quality_score": quality_score,
            "relevance_score": relevance_score,
        }

    async def _analyze_skills(
        self,
        skills_data: List[Dict[str, Any]],
        strategy: SectionOptimizationStrategy,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze skills section"""

        strengths = []
        weaknesses = []
        missing_elements = []
        improvement_opportunities = []
        keyword_gaps = []

        if not skills_data:
            return {
                "strengths": [],
                "weaknesses": ["No skills provided"],
                "missing_elements": ["Skills list"],
                "improvement_opportunities": ["Add relevant skills"],
                "keyword_gaps": [],
                "ats_score": 0.0,
                "quality_score": 0.0,
                "relevance_score": 0.0,
            }

        # Flatten skills list
        all_skills = []
        for skill_category in skills_data:
            if isinstance(skill_category, dict):
                all_skills.extend(skill_category.get("skills", []))
            elif isinstance(skill_category, str):
                all_skills.append(skill_category)

        # Check for categorization
        if len(skills_data) > 1 and all(isinstance(s, dict) for s in skills_data):
            strengths.append("Skills are well categorized")
        else:
            weaknesses.append("Skills are not categorized")
            improvement_opportunities.append(
                "Organize skills into categories (Technical, Soft Skills, etc.)"
            )

        # Check skill count
        if len(all_skills) >= 10:
            strengths.append("Comprehensive skill set")
        elif len(all_skills) < 5:
            weaknesses.append("Limited skill set")
            improvement_opportunities.append("Add more relevant skills")

        # Check for job description match if provided
        if job_description:
            job_skills = self._extract_skills_from_job_description(job_description)
            matching_skills = set(skill.lower() for skill in all_skills) & set(
                job_skills
            )
            missing_skills = set(job_skills) - set(
                skill.lower() for skill in all_skills
            )

            if matching_skills:
                strengths.append(f"Matches {len(matching_skills)} job requirements")

            if missing_skills:
                keyword_gaps.extend(list(missing_skills)[:5])  # Top 5 missing skills
                improvement_opportunities.append("Add job-relevant skills")

        # Calculate scores
        ats_score = min(1.0, len(all_skills) / 15)  # Optimal around 15 skills
        quality_score = len(strengths) / max(1, len(strengths) + len(weaknesses))
        relevance_score = 0.8 if job_description else 0.6

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "missing_elements": missing_elements,
            "improvement_opportunities": improvement_opportunities,
            "keyword_gaps": keyword_gaps,
            "ats_score": ats_score,
            "quality_score": quality_score,
            "relevance_score": relevance_score,
        }

    def _extract_skills_from_job_description(self, job_description: str) -> List[str]:
        """Extract skills from job description text"""

        # Simple skill extraction - in production, this would use NLP
        common_skills = [
            "python",
            "javascript",
            "java",
            "react",
            "node.js",
            "sql",
            "aws",
            "docker",
            "kubernetes",
            "git",
            "agile",
            "scrum",
            "leadership",
            "communication",
            "problem solving",
            "teamwork",
            "project management",
            "data analysis",
        ]

        found_skills = []
        job_lower = job_description.lower()

        for skill in common_skills:
            if skill in job_lower:
                found_skills.append(skill)

        return found_skills

    async def _generate_optimized_content(
        self,
        original_content: Dict[str, Any],
        analysis: SectionAnalysis,
        context: ResumeContext,
        job_description: Optional[str],
        llm_provider: str,
        llm_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate optimized version of section content"""

        # For now, return enhanced version based on analysis
        # In production, this would use LLM to generate optimized content

        optimized = original_content.copy()

        # Apply improvements based on analysis
        if context.current_section == "work_experience":
            optimized = await self._optimize_work_experience_content(
                optimized, analysis
            )
        elif context.current_section == "skills":
            optimized = await self._optimize_skills_content(optimized, analysis)

        return optimized

    async def _optimize_work_experience_content(
        self, content: List[Dict[str, Any]], analysis: SectionAnalysis
    ) -> List[Dict[str, Any]]:
        """Optimize work experience content"""

        optimized = []

        for entry in content:
            optimized_entry = entry.copy()

            # Enhance achievements with action verbs
            if "achievements" in entry:
                enhanced_achievements = []
                for achievement in entry["achievements"]:
                    # Simple enhancement - replace weak verbs
                    enhanced = achievement
                    enhanced = re.sub(
                        r"^worked on", "Developed", enhanced, flags=re.IGNORECASE
                    )
                    enhanced = re.sub(
                        r"^responsible for", "Managed", enhanced, flags=re.IGNORECASE
                    )
                    enhanced = re.sub(
                        r"^helped", "Assisted in", enhanced, flags=re.IGNORECASE
                    )
                    enhanced_achievements.append(enhanced)

                optimized_entry["achievements"] = enhanced_achievements

            optimized.append(optimized_entry)

        return optimized

    async def _optimize_skills_content(
        self, content: List[Dict[str, Any]], analysis: SectionAnalysis
    ) -> List[Dict[str, Any]]:
        """Optimize skills content"""

        # If skills are not categorized, categorize them
        if not all(isinstance(item, dict) for item in content):
            # Simple categorization
            technical_skills = []
            soft_skills = []

            for item in content:
                if isinstance(item, str):
                    # Simple heuristic for categorization
                    if any(
                        tech in item.lower()
                        for tech in ["python", "java", "sql", "aws", "docker"]
                    ):
                        technical_skills.append(item)
                    else:
                        soft_skills.append(item)
                elif isinstance(item, dict):
                    technical_skills.extend(item.get("skills", []))

            return [
                {"category": "Technical Skills", "skills": technical_skills},
                {"category": "Soft Skills", "skills": soft_skills},
            ]

        return content

    async def _generate_section_suggestions(
        self,
        original: Dict[str, Any],
        optimized: Dict[str, Any],
        analysis: SectionAnalysis,
        context: ResumeContext,
    ) -> List[Suggestion]:
        """Generate specific suggestions for section improvement"""

        suggestions = []

        # Generate suggestions based on analysis weaknesses
        for weakness in analysis.weaknesses:
            if "quantified achievements" in weakness:
                suggestions.append(
                    Suggestion(
                        type="content",
                        title="Add Quantified Achievements",
                        description="Include specific numbers, percentages, and metrics to demonstrate impact",
                        impact_score=0.9,
                        reasoning="Quantified achievements are more compelling and memorable to recruiters",
                        section=context.current_section,
                        confidence=0.8,
                    )
                )

            elif "action verbs" in weakness:
                suggestions.append(
                    Suggestion(
                        type="content",
                        title="Use Stronger Action Verbs",
                        description="Start bullet points with powerful action verbs that demonstrate leadership and impact",
                        impact_score=0.7,
                        reasoning="Strong action verbs create more dynamic and engaging descriptions",
                        section=context.current_section,
                        confidence=0.9,
                    )
                )

        # Generate suggestions based on missing elements
        for missing in analysis.missing_elements:
            suggestions.append(
                Suggestion(
                    type="structure",
                    title=f"Add Missing {missing}",
                    description=f"Include {missing} to complete your {context.current_section} section",
                    impact_score=0.6,
                    reasoning=f"{missing} is important for ATS parsing and recruiter review",
                    section=context.current_section,
                    confidence=0.8,
                )
            )

        return suggestions

    async def _calculate_improvement_metrics(
        self,
        original: Dict[str, Any],
        optimized: Dict[str, Any],
        context: ResumeContext,
    ) -> ImprovementMetrics:
        """Calculate improvement metrics between original and optimized content"""

        # Simple scoring - in production, this would be more sophisticated
        before_score = 0.6  # Baseline score
        after_score = 0.8  # Improved score

        return ImprovementMetrics(
            before_score=before_score,
            after_score=after_score,
            improvement_percentage=(after_score - before_score) * 100,
            ats_improvement=0.2,
            keyword_improvement=0.15,
            readability_improvement=0.1,
            content_quality_improvement=0.25,
        )

    async def _calculate_keyword_density(
        self, content: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate keyword density in content"""

        # Simple keyword density calculation
        text = json.dumps(content).lower()
        words = text.split()
        total_words = len(words)

        keyword_counts = {}
        for word in words:
            if len(word) > 3:  # Only count meaningful words
                keyword_counts[word] = keyword_counts.get(word, 0) + 1

        # Convert to density (percentage)
        keyword_density = {}
        for word, count in keyword_counts.items():
            if count > 1:  # Only include repeated keywords
                keyword_density[word] = (count / total_words) * 100

        return dict(
            sorted(keyword_density.items(), key=lambda x: x[1], reverse=True)[:10]
        )

    async def _calculate_readability_score(self, content: Dict[str, Any]) -> float:
        """Calculate readability score of content"""

        # Simple readability calculation
        text = json.dumps(content)
        sentences = text.count(".") + text.count("!") + text.count("?")
        words = len(text.split())

        if sentences == 0:
            return 0.5

        avg_sentence_length = words / sentences

        # Simple scoring: shorter sentences = higher readability
        if avg_sentence_length < 15:
            return 0.9
        elif avg_sentence_length < 20:
            return 0.7
        else:
            return 0.5

    async def _generate_changes_summary(
        self, original: Dict[str, Any], optimized: Dict[str, Any]
    ) -> str:
        """Generate a summary of changes made"""

        changes = []

        # Simple change detection
        if original != optimized:
            changes.append("Enhanced content structure and formatting")
            changes.append("Improved action verbs and impact statements")
            changes.append("Optimized for ATS compatibility")

        if not changes:
            changes.append("No significant changes recommended")

        return "; ".join(changes)

    # Validation helper methods

    async def _validate_personal_details(
        self, original: Dict, modified: Dict
    ) -> Dict[str, List[str]]:
        """Validate personal details section"""
        errors = []
        warnings = []
        suggestions = []

        # Check required fields
        required_fields = ["name", "email"]
        for field in required_fields:
            if not modified.get(field):
                errors.append(f"Missing required field: {field}")

        # Validate email format
        email = modified.get("email", "")
        if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("Invalid email format")

        # Check for professional email
        if email and any(
            domain in email.lower()
            for domain in ["@gmail.com", "@yahoo.com", "@hotmail.com"]
        ):
            suggestions.append("Consider using a professional email domain")

        return {"errors": errors, "warnings": warnings, "suggestions": suggestions}

    async def _validate_work_experience(
        self, original: List, modified: List
    ) -> Dict[str, List[str]]:
        """Validate work experience section"""
        errors = []
        warnings = []
        suggestions = []

        if not modified:
            errors.append("Work experience cannot be empty")
            return {"errors": errors, "warnings": warnings, "suggestions": suggestions}

        for i, entry in enumerate(modified):
            # Check required fields
            if not entry.get("title"):
                errors.append(f"Entry {i+1}: Missing job title")
            if not entry.get("company"):
                errors.append(f"Entry {i+1}: Missing company name")

            # Check date format
            from_date = entry.get("from_date")
            to_date = entry.get("to_date")

            if from_date and not re.match(r"^\d{4}-\d{2}$", from_date):
                warnings.append(f"Entry {i+1}: Use YYYY-MM format for dates")

        return {"errors": errors, "warnings": warnings, "suggestions": suggestions}

    async def _validate_education(
        self, original: List, modified: List
    ) -> Dict[str, List[str]]:
        """Validate education section"""
        errors = []
        warnings = []
        suggestions = []

        for i, entry in enumerate(modified):
            if not entry.get("degree"):
                errors.append(f"Entry {i+1}: Missing degree")
            if not entry.get("university"):
                errors.append(f"Entry {i+1}: Missing university/institution")

        return {"errors": errors, "warnings": warnings, "suggestions": suggestions}

    async def _validate_skills(
        self, original: List, modified: List
    ) -> Dict[str, List[str]]:
        """Validate skills section"""
        errors = []
        warnings = []
        suggestions = []

        if not modified:
            errors.append("Skills section cannot be empty")

        # Check for skill categorization
        if len(modified) > 10 and all(isinstance(skill, str) for skill in modified):
            suggestions.append("Consider categorizing skills for better organization")

        return {"errors": errors, "warnings": warnings, "suggestions": suggestions}

    async def _validate_projects(
        self, original: List, modified: List
    ) -> Dict[str, List[str]]:
        """Validate projects section"""
        errors = []
        warnings = []
        suggestions = []

        for i, entry in enumerate(modified):
            if not entry.get("name"):
                errors.append(f"Project {i+1}: Missing project name")
            if not entry.get("summary") and not entry.get("bullets"):
                warnings.append(f"Project {i+1}: Missing description")

        return {"errors": errors, "warnings": warnings, "suggestions": suggestions}

    async def _validate_generic_section(
        self, original: Any, modified: Any
    ) -> Dict[str, List[str]]:
        """Generic validation for unknown sections"""
        errors = []
        warnings = []
        suggestions = []

        if not modified:
            warnings.append("Section appears to be empty")

        return {"errors": errors, "warnings": warnings, "suggestions": suggestions}

    async def _check_cross_section_consistency(
        self, modified: Dict, context: ResumeContext
    ) -> List[str]:
        """Check consistency across resume sections"""
        issues = []

        # This would check for consistency across the entire resume
        # For now, return empty list
        return issues

    async def _check_ats_compatibility(self, content: Dict, section: str) -> List[str]:
        """Check ATS compatibility issues"""
        issues = []

        # Check for complex formatting
        content_str = json.dumps(content)
        if any(char in content_str for char in ["•", "→", "★", "◆"]):
            issues.append("Special characters may not parse correctly in ATS")

        return issues

    async def _calculate_section_quality_score(
        self, content: Dict, section: str, error_count: int, warning_count: int
    ) -> float:
        """Calculate overall quality score for a section"""

        base_score = 1.0

        # Deduct for errors and warnings
        base_score -= error_count * 0.2
        base_score -= warning_count * 0.1

        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, base_score))

    # Additional analysis methods for other sections

    async def _analyze_education(
        self, education_data: List[Dict], strategy: SectionOptimizationStrategy
    ) -> Dict[str, Any]:
        """Analyze education section"""
        strengths = []
        weaknesses = []
        missing_elements = []

        if not education_data:
            return {
                "strengths": [],
                "weaknesses": ["No education information provided"],
                "missing_elements": ["Education entries"],
                "improvement_opportunities": ["Add education background"],
                "ats_score": 0.0,
                "quality_score": 0.0,
                "relevance_score": 0.0,
            }

        for entry in education_data:
            if entry.get("degree") and entry.get("university"):
                strengths.append("Complete education information")
            else:
                if not entry.get("degree"):
                    missing_elements.append("Degree information")
                if not entry.get("university"):
                    missing_elements.append("Institution name")

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "missing_elements": missing_elements,
            "improvement_opportunities": [],
            "ats_score": 0.8,
            "quality_score": 0.7,
            "relevance_score": 0.6,
        }

    async def _analyze_projects(
        self, projects_data: List[Dict], strategy: SectionOptimizationStrategy
    ) -> Dict[str, Any]:
        """Analyze projects section"""
        strengths = []
        weaknesses = []
        improvement_opportunities = []

        if not projects_data:
            return {
                "strengths": [],
                "weaknesses": ["No projects provided"],
                "missing_elements": ["Project entries"],
                "improvement_opportunities": ["Add relevant projects"],
                "ats_score": 0.0,
                "quality_score": 0.0,
                "relevance_score": 0.0,
            }

        for project in projects_data:
            if project.get("technologies"):
                strengths.append("Includes technology stack")
            else:
                improvement_opportunities.append("Add technologies used in projects")

            if project.get("github_url") or project.get("demo_url"):
                strengths.append("Provides project links")
            else:
                improvement_opportunities.append(
                    "Add links to project repositories or demos"
                )

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "missing_elements": [],
            "improvement_opportunities": improvement_opportunities,
            "ats_score": 0.7,
            "quality_score": 0.6,
            "relevance_score": 0.8,
        }

    async def _analyze_generic_section(
        self, section_data: Any, strategy: SectionOptimizationStrategy
    ) -> Dict[str, Any]:
        """Generic analysis for unknown sections"""
        return {
            "strengths": ["Section is present"],
            "weaknesses": [],
            "missing_elements": [],
            "improvement_opportunities": [],
            "ats_score": 0.5,
            "quality_score": 0.5,
            "relevance_score": 0.5,
        }

    # Suggestion generation methods

    async def _generate_content_suggestions(
        self,
        content: Dict,
        strategy: SectionOptimizationStrategy,
        context: ResumeContext,
        focus_areas: List[str] = None,
    ) -> List[Suggestion]:
        """Generate content-based suggestions"""
        suggestions = []

        # Example content suggestions based on section
        if context.current_section == "work_experience":
            suggestions.append(
                Suggestion(
                    type="content",
                    title="Quantify Your Achievements",
                    description="Add specific numbers, percentages, and metrics to demonstrate your impact",
                    impact_score=0.9,
                    reasoning="Quantified achievements are more compelling and memorable",
                    section=context.current_section,
                    confidence=0.8,
                )
            )

        return suggestions

    async def _generate_structure_suggestions(
        self,
        content: Dict,
        strategy: SectionOptimizationStrategy,
        context: ResumeContext,
    ) -> List[Suggestion]:
        """Generate structure-based suggestions"""
        suggestions = []

        suggestions.append(
            Suggestion(
                type="structure",
                title="Improve Section Organization",
                description="Reorganize content for better flow and readability",
                impact_score=0.6,
                reasoning="Well-organized sections are easier to scan and understand",
                section=context.current_section,
                confidence=0.7,
            )
        )

        return suggestions

    async def _generate_keyword_suggestions(
        self,
        content: Dict,
        strategy: SectionOptimizationStrategy,
        context: ResumeContext,
    ) -> List[Suggestion]:
        """Generate keyword-based suggestions"""
        suggestions = []

        suggestions.append(
            Suggestion(
                type="keyword",
                title="Add Industry Keywords",
                description="Include relevant industry keywords to improve ATS compatibility",
                impact_score=0.8,
                reasoning="Keywords help your resume get past ATS filters",
                section=context.current_section,
                confidence=0.8,
            )
        )

        return suggestions

    async def _generate_ats_suggestions(
        self,
        content: Dict,
        strategy: SectionOptimizationStrategy,
        context: ResumeContext,
    ) -> List[Suggestion]:
        """Generate ATS-focused suggestions"""
        suggestions = []

        suggestions.append(
            Suggestion(
                type="formatting",
                title="Optimize for ATS",
                description="Ensure formatting is ATS-friendly with standard fonts and structure",
                impact_score=0.7,
                reasoning="ATS-friendly formatting ensures your resume gets properly parsed",
                section=context.current_section,
                confidence=0.9,
            )
        )

        return suggestions

    async def health_check(self) -> bool:
        """Perform health check for section optimizer"""
        try:
            # Check if database is accessible
            if self.db is None:
                return False
                
            # Check if optimization strategies are loaded
            if not hasattr(self, 'optimization_strategies') or not self.optimization_strategies:
                return False
                
            # Check if action verbs are loaded
            if not hasattr(self, 'action_verbs') or not self.action_verbs:
                return False
                
            # Check if industry keywords are loaded
            if not hasattr(self, 'industry_keywords') or not self.industry_keywords:
                return False
                
            return True
        except Exception as e:
            logger.error(f"SectionOptimizer health check failed: {e}")
            return False
