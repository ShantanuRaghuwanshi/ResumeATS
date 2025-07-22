"""
Feedback Analyzer Service

Provides real-time feedback analysis for resume changes including:
- Change impact analysis
- ATS compatibility checking
- Consistency validation across resume sections
- Performance metrics calculation
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.feedback import (
    ATSCompatibilityResult,
    ConsistencyReport,
    ChangeImpactAnalysis,
    RealTimeFeedback,
)
from models.conversation import ResumeContext
from database import get_database
from configs.config import get_logger

logger = get_logger(__name__)


class FeedbackAnalyzer:
    """Service for analyzing resume changes and providing real-time feedback"""

    def __init__(self):
        self.db = get_database()

    async def analyze_change_impact(
        self, before: Dict[str, Any], after: Dict[str, Any], context: ResumeContext
    ) -> ChangeImpactAnalysis:
        """Analyze the impact of changes made to resume content"""

        try:
            section = context.current_section
            change_type = self._determine_change_type(before, after)

            # Calculate impact scores
            overall_impact = await self._calculate_overall_impact(
                before, after, section
            )
            ats_impact = await self._calculate_ats_impact(before, after, section)
            keyword_impact = await self._calculate_keyword_impact(
                before, after, section
            )
            readability_impact = await self._calculate_readability_impact(before, after)
            relevance_impact = await self._calculate_relevance_impact(
                before, after, context
            )

            # Analyze specific changes
            positive_changes = await self._identify_positive_changes(
                before, after, section
            )
            negative_changes = await self._identify_negative_changes(
                before, after, section
            )
            neutral_changes = await self._identify_neutral_changes(
                before, after, section
            )

            # Generate recommendations
            further_improvements = await self._generate_improvement_recommendations(
                after, section
            )
            warnings = await self._generate_change_warnings(before, after, section)

            analysis = ChangeImpactAnalysis(
                section=section,
                change_type=change_type,
                before_content=before,
                after_content=after,
                overall_impact=overall_impact,
                ats_impact=ats_impact,
                keyword_impact=keyword_impact,
                readability_impact=readability_impact,
                relevance_impact=relevance_impact,
                positive_changes=positive_changes,
                negative_changes=negative_changes,
                neutral_changes=neutral_changes,
                further_improvements=further_improvements,
                warnings=warnings,
            )

            # Store analysis
            self.db.create(
                "change_impact_analyses", analysis.change_id, analysis.model_dump()
            )

            logger.info(f"Analyzed change impact for section {section}")
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze change impact: {e}")
            raise

    async def check_ats_compatibility(
        self, content: Dict[str, Any], section: str = None
    ) -> ATSCompatibilityResult:
        """Check ATS compatibility of resume content"""

        try:
            # Initialize scores
            parsing_score = 1.0
            formatting_score = 1.0
            keyword_score = 1.0
            structure_score = 1.0

            # Initialize issue lists
            formatting_issues = []
            parsing_issues = []
            missing_sections = []
            problematic_elements = []
            recommendations = []
            quick_fixes = []

            # Check for problematic formatting
            content_text = str(content)
            problematic_chars = ["•", "→", "★", "◆", "▪"]
            for char in problematic_chars:
                if char in content_text:
                    formatting_issues.append(
                        f"Contains potentially problematic character: {char}"
                    )
                    formatting_score -= 0.1
                    quick_fixes.append(f"Replace {char} with standard bullet points")

            # Check for standard structure
            if section == "work_experience" and isinstance(content, list):
                for entry in content:
                    if isinstance(entry, dict):
                        if not entry.get("title"):
                            parsing_issues.append("Missing job title")
                            parsing_score -= 0.2
                        if not entry.get("company"):
                            parsing_issues.append("Missing company name")
                            parsing_score -= 0.2

            # Check for keywords
            if section:
                keyword_density = await self._calculate_keyword_density(
                    content_text, section
                )
                if sum(keyword_density.values()) < 0.02:  # Less than 2% keyword density
                    keyword_score -= 0.3
                    recommendations.append("Add more relevant keywords")

            # Ensure scores don't go below 0
            parsing_score = max(0.0, parsing_score)
            formatting_score = max(0.0, formatting_score)
            keyword_score = max(0.0, keyword_score)
            structure_score = max(0.0, structure_score)

            # Calculate overall score
            overall_score = (
                parsing_score + formatting_score + keyword_score + structure_score
            ) / 4

            result = ATSCompatibilityResult(
                overall_score=overall_score,
                parsing_score=parsing_score,
                formatting_score=formatting_score,
                keyword_score=keyword_score,
                structure_score=structure_score,
                formatting_issues=formatting_issues,
                parsing_issues=parsing_issues,
                missing_sections=missing_sections,
                problematic_elements=problematic_elements,
                recommendations=recommendations,
                quick_fixes=quick_fixes,
            )

            logger.info(
                f"ATS compatibility check completed with score: {overall_score:.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to check ATS compatibility: {e}")
            raise

    async def validate_consistency(self, resume: Dict[str, Any]) -> ConsistencyReport:
        """Validate consistency across resume sections"""

        try:
            # Initialize consistency scores
            date_consistency = True
            formatting_consistency = True
            tone_consistency = True
            terminology_consistency = True

            # Initialize issue lists
            date_conflicts = []
            formatting_inconsistencies = []
            tone_variations = []
            terminology_conflicts = []
            skill_redundancy = []
            missing_cross_references = []
            contradictory_information = []
            recommendations = []

            # Check date consistency
            work_dates = []
            if "work_experience" in resume:
                for entry in resume["work_experience"]:
                    if isinstance(entry, dict):
                        from_date = entry.get("from_date")
                        to_date = entry.get("to_date")
                        if from_date:
                            work_dates.append(str(from_date))
                        if to_date and str(to_date).lower() != "present":
                            work_dates.append(str(to_date))

            # Check for inconsistent date formats
            date_formats = set()
            for date in work_dates:
                if re.match(r"^\d{4}$", date):
                    date_formats.add("year_only")
                elif re.match(r"^\d{1,2}/\d{4}$", date):
                    date_formats.add("month_year_slash")
                elif re.match(r"^\w+ \d{4}$", date):
                    date_formats.add("month_year_text")

            if len(date_formats) > 1:
                date_consistency = False
                date_conflicts.append("Inconsistent date formatting across entries")
                recommendations.append("Use consistent date format throughout resume")

            # Check formatting consistency
            sections_with_lists = ["work_experience", "education", "projects", "skills"]
            bullet_styles = set()

            for section in sections_with_lists:
                if section in resume:
                    section_text = str(resume[section])
                    if "•" in section_text:
                        bullet_styles.add("bullet")
                    elif "-" in section_text:
                        bullet_styles.add("dash")
                    elif "*" in section_text:
                        bullet_styles.add("asterisk")

            if len(bullet_styles) > 1:
                formatting_consistency = False
                formatting_inconsistencies.append("Inconsistent bullet point styles")
                recommendations.append(
                    "Use consistent bullet point style throughout resume"
                )

            # Check tone consistency
            text_sections = []
            if "personal_details" in resume and isinstance(
                resume["personal_details"], dict
            ):
                if "summary" in resume["personal_details"]:
                    text_sections.append(resume["personal_details"]["summary"])

            if "work_experience" in resume:
                for entry in resume["work_experience"]:
                    if isinstance(entry, dict) and "summary" in entry:
                        text_sections.append(entry["summary"])

            first_person_count = 0
            third_person_count = 0

            for text in text_sections:
                text_lower = str(text).lower()
                if any(word in text_lower for word in ["i ", "my ", "me "]):
                    first_person_count += 1
                else:
                    third_person_count += 1

            if first_person_count > 0 and third_person_count > 0:
                tone_consistency = False
                tone_variations.append("Mixed first and third person voice")
                recommendations.append(
                    "Use consistent voice throughout resume (preferably third person)"
                )

            # Check skill redundancy
            skills_section = set()
            work_skills = set()

            if "skills" in resume:
                for skill_group in resume["skills"]:
                    if isinstance(skill_group, dict) and "skills" in skill_group:
                        skills_section.update(s.lower() for s in skill_group["skills"])
                    elif isinstance(skill_group, str):
                        skills_section.add(skill_group.lower())

            if "work_experience" in resume:
                for entry in resume["work_experience"]:
                    if isinstance(entry, dict):
                        entry_text = str(entry).lower()
                        common_skills = [
                            "python",
                            "javascript",
                            "management",
                            "leadership",
                            "analysis",
                        ]
                        for skill in common_skills:
                            if skill in entry_text:
                                work_skills.add(skill)

            redundant_skills = skills_section.intersection(work_skills)
            if len(redundant_skills) > 3:
                skill_redundancy.append("High skill redundancy between sections")
                recommendations.append("Consider consolidating repeated skills")

            # Calculate overall consistency score
            consistency_flags = [
                date_consistency,
                formatting_consistency,
                tone_consistency,
                terminology_consistency,
            ]
            overall_consistency_score = sum(consistency_flags) / len(consistency_flags)

            # Reduce score based on number of issues
            total_issues = (
                len(date_conflicts)
                + len(formatting_inconsistencies)
                + len(tone_variations)
                + len(terminology_conflicts)
                + len(skill_redundancy)
                + len(missing_cross_references)
                + len(contradictory_information)
            )

            if total_issues > 0:
                overall_consistency_score *= max(0.3, 1.0 - (total_issues * 0.1))

            report = ConsistencyReport(
                overall_consistency_score=overall_consistency_score,
                date_consistency=date_consistency,
                formatting_consistency=formatting_consistency,
                tone_consistency=tone_consistency,
                terminology_consistency=terminology_consistency,
                date_conflicts=date_conflicts,
                formatting_inconsistencies=formatting_inconsistencies,
                tone_variations=tone_variations,
                terminology_conflicts=terminology_conflicts,
                skill_redundancy=skill_redundancy,
                missing_cross_references=missing_cross_references,
                contradictory_information=contradictory_information,
                recommendations=list(set(recommendations)),
            )

            logger.info(
                f"Consistency validation completed with score: {overall_consistency_score:.2f}"
            )
            return report

        except Exception as e:
            logger.error(f"Failed to validate consistency: {e}")
            raise

    async def generate_real_time_feedback(
        self,
        session_id: str,
        section: str,
        current_content: str,
        previous_content: str = None,
    ) -> RealTimeFeedback:
        """Generate real-time feedback for live editing"""

        try:
            # Calculate basic metrics
            character_count = len(current_content)
            word_count = len(current_content.split())

            # Calculate readability score
            readability_score = await self._calculate_readability_score(current_content)

            # Calculate keyword density
            keyword_density = await self._calculate_keyword_density(
                current_content, section
            )

            # Identify issues and suggestions
            grammar_issues = await self._identify_grammar_issues(current_content)
            style_suggestions = await self._generate_style_suggestions(
                current_content, section
            )
            keyword_suggestions = await self._generate_keyword_suggestions(
                current_content, section
            )

            # Calculate quality scores
            current_quality_score = await self._calculate_content_quality_score(
                current_content, section
            )
            ats_compatibility = await self._calculate_ats_score(
                current_content, section
            )

            # Calculate improvement since last version
            improvement_since_last = None
            if previous_content:
                previous_quality = await self._calculate_content_quality_score(
                    previous_content, section
                )
                improvement_since_last = current_quality_score - previous_quality

            feedback = RealTimeFeedback(
                session_id=session_id,
                section=section,
                current_content=current_content,
                character_count=character_count,
                word_count=word_count,
                readability_score=readability_score,
                keyword_density=keyword_density,
                grammar_issues=grammar_issues,
                style_suggestions=style_suggestions,
                keyword_suggestions=keyword_suggestions,
                current_quality_score=current_quality_score,
                ats_compatibility=ats_compatibility,
                improvement_since_last=improvement_since_last,
            )

            logger.info(f"Generated real-time feedback for section {section}")
            return feedback

        except Exception as e:
            logger.error(f"Failed to generate real-time feedback: {e}")
            raise

    # Private helper methods

    def _determine_change_type(
        self, before: Dict[str, Any], after: Dict[str, Any]
    ) -> str:
        """Determine the type of change made"""

        if not before:
            return "addition"
        elif not after:
            return "deletion"
        elif len(str(after)) > len(str(before)) * 1.2:
            return "addition"
        elif len(str(after)) < len(str(before)) * 0.8:
            return "deletion"
        else:
            return "modification"

    async def _calculate_overall_impact(
        self, before: Dict[str, Any], after: Dict[str, Any], section: str
    ) -> float:
        """Calculate overall impact score of changes"""

        try:
            before_quality = await self._calculate_content_quality_score(
                str(before), section
            )
            after_quality = await self._calculate_content_quality_score(
                str(after), section
            )
            return after_quality - before_quality
        except Exception:
            return 0.0

    async def _calculate_ats_impact(
        self, before: Dict[str, Any], after: Dict[str, Any], section: str
    ) -> float:
        """Calculate ATS compatibility impact of changes"""

        try:
            before_ats = await self._calculate_ats_score(str(before), section)
            after_ats = await self._calculate_ats_score(str(after), section)
            return after_ats - before_ats
        except Exception:
            return 0.0

    async def _calculate_keyword_impact(
        self, before: Dict[str, Any], after: Dict[str, Any], section: str
    ) -> float:
        """Calculate keyword optimization impact of changes"""

        try:
            before_keywords = await self._calculate_keyword_density(
                str(before), section
            )
            after_keywords = await self._calculate_keyword_density(str(after), section)

            before_total = sum(before_keywords.values()) if before_keywords else 0
            after_total = sum(after_keywords.values()) if after_keywords else 0

            return (after_total - before_total) / max(1, before_total)
        except Exception:
            return 0.0

    async def _calculate_readability_impact(
        self, before: Dict[str, Any], after: Dict[str, Any]
    ) -> float:
        """Calculate readability impact of changes"""

        try:
            before_readability = await self._calculate_readability_score(str(before))
            after_readability = await self._calculate_readability_score(str(after))
            return after_readability - before_readability
        except Exception:
            return 0.0

    async def _calculate_relevance_impact(
        self, before: Dict[str, Any], after: Dict[str, Any], context: ResumeContext
    ) -> float:
        """Calculate relevance impact of changes"""

        try:
            before_text = str(before).lower()
            after_text = str(after).lower()

            relevant_keywords = [
                "experience",
                "skill",
                "project",
                "achievement",
                "result",
                "impact",
            ]

            before_count = sum(
                1 for keyword in relevant_keywords if keyword in before_text
            )
            after_count = sum(
                1 for keyword in relevant_keywords if keyword in after_text
            )

            return (after_count - before_count) / max(1, len(relevant_keywords))
        except Exception:
            return 0.0

    async def _identify_positive_changes(
        self, before: Dict[str, Any], after: Dict[str, Any], section: str
    ) -> List[str]:
        """Identify positive changes made"""

        positive_changes = []

        try:
            before_text = str(before).lower()
            after_text = str(after).lower()

            # Check for addition of quantified achievements
            if section == "work_experience":
                before_numbers = len(re.findall(r"\d+%|\$\d+|\d+\+", before_text))
                after_numbers = len(re.findall(r"\d+%|\$\d+|\d+\+", after_text))

                if after_numbers > before_numbers:
                    positive_changes.append("Added quantified achievements")

            # Check for improved action verbs
            strong_verbs = [
                "led",
                "managed",
                "developed",
                "created",
                "implemented",
                "improved",
                "achieved",
            ]
            before_verbs = sum(1 for verb in strong_verbs if verb in before_text)
            after_verbs = sum(1 for verb in strong_verbs if verb in after_text)

            if after_verbs > before_verbs:
                positive_changes.append("Improved action verbs")

            # Check for better structure
            if len(after_text) > len(before_text) * 1.1:
                positive_changes.append("Added more detailed content")

        except Exception as e:
            logger.error(f"Error identifying positive changes: {e}")

        return positive_changes

    async def _identify_negative_changes(
        self, before: Dict[str, Any], after: Dict[str, Any], section: str
    ) -> List[str]:
        """Identify negative changes made"""

        negative_changes = []

        try:
            before_text = str(before).lower()
            after_text = str(after).lower()

            # Check for removal of important content
            if len(after_text) < len(before_text) * 0.7:
                negative_changes.append("Removed significant content")

            # Check for removal of quantified achievements
            if section == "work_experience":
                before_numbers = len(re.findall(r"\d+%|\$\d+|\d+\+", before_text))
                after_numbers = len(re.findall(r"\d+%|\$\d+|\d+\+", after_text))

                if after_numbers < before_numbers:
                    negative_changes.append("Removed quantified achievements")

            # Check for weaker action verbs
            weak_verbs = ["worked", "helped", "responsible", "duties"]
            before_weak = sum(1 for verb in weak_verbs if verb in before_text)
            after_weak = sum(1 for verb in weak_verbs if verb in after_text)

            if after_weak > before_weak:
                negative_changes.append("Added weak action verbs")

        except Exception as e:
            logger.error(f"Error identifying negative changes: {e}")

        return negative_changes

    async def _identify_neutral_changes(
        self, before: Dict[str, Any], after: Dict[str, Any], section: str
    ) -> List[str]:
        """Identify neutral changes made"""

        neutral_changes = []

        try:
            before_words = set(str(before).lower().split())
            after_words = set(str(after).lower().split())

            added_words = after_words - before_words
            removed_words = before_words - after_words

            if added_words and removed_words and len(added_words) == len(removed_words):
                neutral_changes.append("Made word substitutions")

            # Check for formatting changes
            if (
                len(str(before)) != len(str(after))
                and abs(len(str(before)) - len(str(after))) < 10
            ):
                neutral_changes.append("Minor formatting adjustments")

        except Exception as e:
            logger.error(f"Error identifying neutral changes: {e}")

        return neutral_changes

    async def _generate_improvement_recommendations(
        self, content: Dict[str, Any], section: str
    ) -> List[str]:
        """Generate recommendations for further improvements"""

        recommendations = []

        try:
            content_text = str(content).lower()

            # Section-specific recommendations
            if section == "work_experience":
                # Check for quantified achievements
                if not re.search(r"\d+%|\$\d+|\d+\+", content_text):
                    recommendations.append("Add quantified achievements and metrics")

                # Check for action verbs
                weak_verbs = ["worked", "helped", "responsible", "duties"]
                if any(verb in content_text for verb in weak_verbs):
                    recommendations.append(
                        "Replace weak verbs with strong action verbs"
                    )

                # Check for impact statements
                impact_words = [
                    "improved",
                    "increased",
                    "reduced",
                    "achieved",
                    "delivered",
                ]
                if not any(word in content_text for word in impact_words):
                    recommendations.append("Add impact statements showing results")

            elif section == "skills":
                # Check for skill categorization
                if isinstance(content, list) and len(content) > 10:
                    recommendations.append("Consider categorizing skills by type")

                # Check for skill levels
                if "beginner" not in content_text and "advanced" not in content_text:
                    recommendations.append("Consider adding skill proficiency levels")

            elif section == "education":
                # Check for GPA
                if "gpa" not in content_text and "grade" not in content_text:
                    recommendations.append("Consider adding GPA if above 3.5")

                # Check for relevant coursework
                if "coursework" not in content_text:
                    recommendations.append("Add relevant coursework if applicable")

            # General recommendations
            if len(content_text) < 50:
                recommendations.append("Consider adding more detailed content")

            if len(content_text) > 500:
                recommendations.append(
                    "Consider condensing content for better readability"
                )

        except Exception as e:
            logger.error(f"Error generating improvement recommendations: {e}")

        return recommendations

    async def _generate_change_warnings(
        self, before: Dict[str, Any], after: Dict[str, Any], section: str
    ) -> List[str]:
        """Generate warnings about potentially problematic changes"""

        warnings = []

        try:
            before_text = str(before).lower()
            after_text = str(after).lower()

            # Check for significant content reduction
            if len(after_text) < len(before_text) * 0.5:
                warnings.append("Significant content reduction may impact completeness")

            # Check for removal of important keywords
            important_keywords = [
                "experience",
                "skill",
                "project",
                "achievement",
                "result",
            ]
            for keyword in important_keywords:
                if keyword in before_text and keyword not in after_text:
                    warnings.append(f"Removed important keyword: {keyword}")

            # Check for formatting issues
            if section == "work_experience":
                # Check for missing dates
                if "20" in before_text and "20" not in after_text:
                    warnings.append("Removed date information")

                # Check for missing company names
                if len(re.findall(r"[A-Z][a-z]+ [A-Z][a-z]+", before_text)) > len(
                    re.findall(r"[A-Z][a-z]+ [A-Z][a-z]+", after_text)
                ):
                    warnings.append("Potentially removed company names")

            # Check for ATS compatibility issues
            problematic_chars = ["•", "→", "★", "◆", "▪"]
            for char in problematic_chars:
                if char not in before_text and char in after_text:
                    warnings.append(
                        f"Added potentially ATS-problematic character: {char}"
                    )

        except Exception as e:
            logger.error(f"Error generating change warnings: {e}")

        return warnings

    async def _calculate_keyword_density(
        self, content: str, section: str
    ) -> Dict[str, float]:
        """Calculate keyword density for the content"""

        try:
            content_lower = content.lower()
            words = content_lower.split()
            total_words = len(words)

            if total_words == 0:
                return {}

            # Section-specific keywords
            section_keywords = {
                "work_experience": [
                    "managed",
                    "led",
                    "developed",
                    "created",
                    "implemented",
                    "improved",
                    "achieved",
                    "delivered",
                    "coordinated",
                    "supervised",
                ],
                "skills": [
                    "python",
                    "javascript",
                    "java",
                    "react",
                    "node",
                    "sql",
                    "aws",
                    "docker",
                    "kubernetes",
                    "git",
                    "agile",
                ],
                "education": [
                    "bachelor",
                    "master",
                    "degree",
                    "university",
                    "college",
                    "gpa",
                    "coursework",
                    "thesis",
                    "research",
                ],
                "projects": [
                    "built",
                    "designed",
                    "developed",
                    "created",
                    "implemented",
                    "deployed",
                    "optimized",
                    "integrated",
                ],
            }

            keywords = section_keywords.get(section, [])
            keyword_density = {}

            for keyword in keywords:
                count = content_lower.count(keyword)
                density = count / total_words
                if density > 0:
                    keyword_density[keyword] = density

            return keyword_density

        except Exception as e:
            logger.error(f"Error calculating keyword density: {e}")
            return {}

    async def _calculate_readability_score(self, content: str) -> float:
        """Calculate readability score using simple metrics"""

        try:
            if not content:
                return 0.0

            # Simple readability metrics
            sentences = len(re.split(r"[.!?]+", content))
            words = len(content.split())
            characters = len(content.replace(" ", ""))

            if sentences == 0 or words == 0:
                return 0.0

            # Average sentence length
            avg_sentence_length = words / sentences

            # Average word length
            avg_word_length = characters / words

            # Simple readability score (higher is better, max 1.0)
            # Penalize very long sentences and very long words
            sentence_score = max(0, 1.0 - (avg_sentence_length - 15) / 20)
            word_score = max(0, 1.0 - (avg_word_length - 5) / 5)

            readability_score = (sentence_score + word_score) / 2
            return min(1.0, max(0.0, readability_score))

        except Exception as e:
            logger.error(f"Error calculating readability score: {e}")
            return 0.5

    async def _identify_grammar_issues(self, content: str) -> List[str]:
        """Identify basic grammar issues in content"""

        issues = []

        try:
            # Basic grammar checks
            if not content:
                return issues

            # Check for double spaces
            if "  " in content:
                issues.append("Multiple consecutive spaces found")

            # Check for missing capitalization at sentence start
            sentences = re.split(r"[.!?]+", content)
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and not sentence[0].isupper():
                    issues.append("Sentence should start with capital letter")
                    break

            # Check for repeated words
            words = content.lower().split()
            for i in range(len(words) - 1):
                if words[i] == words[i + 1]:
                    issues.append(f"Repeated word: {words[i]}")

            # Check for common typos
            common_typos = {
                "teh": "the",
                "adn": "and",
                "recieve": "receive",
                "seperate": "separate",
            }

            content_lower = content.lower()
            for typo, correction in common_typos.items():
                if typo in content_lower:
                    issues.append(f"Possible typo: '{typo}' should be '{correction}'")

        except Exception as e:
            logger.error(f"Error identifying grammar issues: {e}")

        return issues

    async def _generate_style_suggestions(
        self, content: str, section: str
    ) -> List[str]:
        """Generate style improvement suggestions"""

        suggestions = []

        try:
            content_lower = content.lower()

            # Section-specific style suggestions
            if section == "work_experience":
                # Check for passive voice
                passive_indicators = ["was", "were", "been", "being"]
                if any(indicator in content_lower for indicator in passive_indicators):
                    suggestions.append(
                        "Consider using active voice instead of passive voice"
                    )

                # Check for first person
                if any(word in content_lower for word in ["i ", "my ", "me "]):
                    suggestions.append("Use third person instead of first person")

                # Check for weak verbs
                weak_verbs = ["worked", "helped", "responsible", "duties"]
                if any(verb in content_lower for verb in weak_verbs):
                    suggestions.append("Replace weak verbs with strong action verbs")

            elif section == "summary" or section == "objective":
                # Check length
                if len(content) > 300:
                    suggestions.append("Consider shortening summary for better impact")

                if len(content) < 50:
                    suggestions.append("Consider expanding summary with more details")

            # General style suggestions
            if content.count(",") > content.count(".") * 2:
                suggestions.append("Consider breaking long sentences into shorter ones")

            if not any(char.isupper() for char in content):
                suggestions.append("Ensure proper capitalization")

        except Exception as e:
            logger.error(f"Error generating style suggestions: {e}")

        return suggestions

    async def _generate_keyword_suggestions(
        self, content: str, section: str
    ) -> List[str]:
        """Generate keyword optimization suggestions"""

        suggestions = []

        try:
            content_lower = content.lower()

            # Section-specific keyword suggestions
            if section == "work_experience":
                missing_keywords = []
                important_keywords = [
                    "managed",
                    "led",
                    "developed",
                    "created",
                    "implemented",
                    "improved",
                    "achieved",
                    "delivered",
                    "coordinated",
                ]

                for keyword in important_keywords:
                    if keyword not in content_lower:
                        missing_keywords.append(keyword)

                if missing_keywords:
                    suggestions.append(
                        f"Consider adding action words: {', '.join(missing_keywords[:3])}"
                    )

            elif section == "skills":
                # Suggest adding skill categories
                if (
                    "programming" not in content_lower
                    and "languages" not in content_lower
                ):
                    suggestions.append(
                        "Consider categorizing skills (e.g., Programming Languages, Tools)"
                    )

            elif section == "summary":
                # Suggest industry keywords
                if "experience" not in content_lower:
                    suggestions.append("Consider mentioning years of experience")

                if "specialist" not in content_lower and "expert" not in content_lower:
                    suggestions.append("Consider adding expertise indicators")

            # General keyword suggestions
            keyword_density = await self._calculate_keyword_density(content, section)
            if sum(keyword_density.values()) < 0.02:  # Less than 2% keyword density
                suggestions.append("Consider adding more relevant industry keywords")

        except Exception as e:
            logger.error(f"Error generating keyword suggestions: {e}")

        return suggestions

    async def _calculate_content_quality_score(
        self, content: str, section: str
    ) -> float:
        """Calculate overall content quality score"""

        try:
            if not content:
                return 0.0

            # Initialize score components
            length_score = 0.0
            keyword_score = 0.0
            structure_score = 0.0
            readability_score = 0.0

            # Length scoring (section-specific)
            content_length = len(content)
            if section == "work_experience":
                # Optimal length: 100-300 characters per entry
                if 100 <= content_length <= 300:
                    length_score = 1.0
                elif content_length < 100:
                    length_score = content_length / 100
                else:
                    length_score = max(0.5, 1.0 - (content_length - 300) / 200)
            elif section == "summary":
                # Optimal length: 50-150 characters
                if 50 <= content_length <= 150:
                    length_score = 1.0
                elif content_length < 50:
                    length_score = content_length / 50
                else:
                    length_score = max(0.5, 1.0 - (content_length - 150) / 100)
            else:
                # General length scoring
                if 30 <= content_length <= 200:
                    length_score = 1.0
                else:
                    length_score = 0.7

            # Keyword scoring
            keyword_density = await self._calculate_keyword_density(content, section)
            total_keyword_density = sum(keyword_density.values())
            keyword_score = min(1.0, total_keyword_density * 20)  # Scale up density

            # Structure scoring
            structure_score = await self._calculate_structure_score(content, section)

            # Readability scoring
            readability_score = await self._calculate_readability_score(content)

            # Weighted average
            quality_score = (
                length_score * 0.25
                + keyword_score * 0.30
                + structure_score * 0.25
                + readability_score * 0.20
            )

            return min(1.0, max(0.0, quality_score))

        except Exception as e:
            logger.error(f"Error calculating content quality score: {e}")
            return 0.5

    async def _calculate_ats_score(self, content: str, section: str) -> float:
        """Calculate ATS compatibility score"""

        try:
            if not content:
                return 0.0

            score = 1.0

            # Check for problematic characters
            problematic_chars = ["•", "→", "★", "◆", "▪", "◊", "►"]
            for char in problematic_chars:
                if char in content:
                    score -= 0.1

            # Check for proper structure
            if section == "work_experience":
                # Should have dates
                if not re.search(r"20\d{2}", content):
                    score -= 0.2

                # Should have company/title structure
                if not re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", content):
                    score -= 0.1

            # Check for standard formatting
            if section in ["education", "work_experience"]:
                # Should have proper date format
                inconsistent_dates = (
                    len(
                        set(
                            [
                                bool(re.search(r"\d{4}", content)),
                                bool(re.search(r"\d{1,2}/\d{4}", content)),
                                bool(re.search(r"\w+ \d{4}", content)),
                            ]
                        )
                    )
                    > 1
                )

                if inconsistent_dates:
                    score -= 0.15

            # Ensure score is within bounds
            return min(1.0, max(0.0, score))

        except Exception as e:
            logger.error(f"Error calculating ATS score: {e}")
            return 0.7

    async def _calculate_structure_score(self, content: str, section: str) -> float:
        """Calculate structure quality score"""

        try:
            if not content:
                return 0.0

            score = 0.5  # Base score

            # Section-specific structure checks
            if section == "work_experience":
                # Check for proper bullet points or structure
                if "•" in content or "-" in content or "*" in content:
                    score += 0.2

                # Check for dates
                if re.search(r"20\d{2}", content):
                    score += 0.2

                # Check for company/title
                if re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", content):
                    score += 0.1

            elif section == "education":
                # Check for degree and institution
                degree_words = ["bachelor", "master", "phd", "degree", "certificate"]
                if any(word in content.lower() for word in degree_words):
                    score += 0.2

                # Check for graduation date
                if re.search(r"20\d{2}", content):
                    score += 0.2

            elif section == "skills":
                # Check for categorization
                if ":" in content or "," in content:
                    score += 0.3

            # General structure checks
            sentences = len(re.split(r"[.!?]+", content))
            if sentences > 1:
                score += 0.1

            return min(1.0, max(0.0, score))

        except Exception as e:
            logger.error(f"Error calculating structure score: {e}")
            return 0.5
