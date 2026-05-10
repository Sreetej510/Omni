"""Quality validation for research results."""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re


@dataclass
class ValidationResult:
    """Result of research quality validation."""
    passed: bool
    score: float
    issues: List[str]
    recommendations: List[str]
    reference_count: int
    source_diversity: float
    content_quality: float


class QualityValidator:
    """Validate research quality against dynamic thresholds."""
    
    def __init__(
        self,
        min_references_default: int = 5,
        min_content_length: int = 500,
        max_single_source_percentage: float = 0.40
    ):
        self.min_references_default = min_references_default
        self.min_content_length = min_content_length
        self.max_single_source_percentage = max_single_source_percentage
    
    def validate(self, subagent_results: Dict[str, str], topic: str) -> ValidationResult:
        """
        Validate research quality for all subagents.
        
        Args:
            subagent_results: Dictionary of subagent names to their findings
            topic: Original research topic
            
        Returns:
            ValidationResult with detailed feedback
        """
        all_issues = []
        all_recommendations = []
        total_score = 0.0
        
        # Get dynamic threshold
        min_references = self.get_dynamic_threshold(topic)
        
        for agent_name, findings in subagent_results.items():
            # Validate each subagent
            result = self._validate_single_agent(findings, min_references, agent_name)
            
            all_issues.extend(result.issues)
            all_recommendations.extend(result.recommendations)
            total_score += result.score
        
        # Calculate average score
        avg_score = total_score / len(subagent_results) if subagent_results else 0.0
        
        # Overall pass/fail
        passed = (
            avg_score >= 0.7 and
            all(len(r.issues) == 0 for r in [
                self._validate_single_agent(f, min_references, n)
                for n, f in subagent_results.items()
            ])
        )
        
        return ValidationResult(
            passed=passed,
            score=avg_score,
            issues=all_issues,
            recommendations=all_recommendations,
            reference_count=sum(self._count_references(f) for f in subagent_results.values()),
            source_diversity=self._calculate_source_diversity(subagent_results),
            content_quality=self._calculate_content_quality(subagent_results)
        )
    
    def _validate_single_agent(
        self,
        findings: str,
        min_references: int,
        agent_name: str
    ) -> ValidationResult:
        """Validate a single agent's research."""
        issues = []
        recommendations = []
        score = 1.0
        
        # Check reference count
        ref_count = self._count_references(findings)
        if ref_count < min_references:
            issues.append(f"{agent_name}: Only {ref_count} references (minimum: {min_references})")
            recommendations.append(f"{agent_name}: Conduct more searches to find additional sources")
            score -= 0.3
        
        # Check content length
        content_length = len(findings)
        if content_length < self.min_content_length:
            issues.append(f"{agent_name}: Content too short ({content_length} chars)")
            recommendations.append(f"{agent_name}: Expand research with more detailed findings")
            score -= 0.2
        
        # Check source diversity
        sources = self._extract_sources(findings)
        if sources:
            source_counts = {}
            for source in sources:
                domain = self._get_domain(source)
                source_counts[domain] = source_counts.get(domain, 0) + 1
            
            total_sources = len(sources)
            for domain, count in source_counts.items():
                percentage = count / total_sources
                if percentage > self.max_single_source_percentage:
                    issues.append(f"{agent_name}: Too many sources from {domain} ({percentage:.0%})")
                    recommendations.append(f"{agent_name}: Diversify sources beyond {domain}")
                    score -= 0.1
        
        # Check for URL content
        if not self._has_url_content(findings):
            recommendations.append(f"{agent_name}: Fetch and include content from URLs")
        
        return ValidationResult(
            passed=score >= 0.7,
            score=max(0.0, score),
            issues=issues,
            recommendations=recommendations,
            reference_count=ref_count,
            source_diversity=1.0 - (len(source_counts) / max(len(sources), 1)) if sources else 0.0,
            content_quality=min(1.0, content_length / 2000)
        )
    
    def get_dynamic_threshold(self, topic: str) -> int:
        """
        Determine minimum reference count based on topic complexity.
        
        Args:
            topic: Research topic
            
        Returns:
            Minimum number of references required
        """
        # Analyze topic complexity
        topic_lower = topic.lower()
        
        # Count complexity indicators
        complexity_score = 0
        
        # Length-based complexity
        word_count = len(topic.split())
        if word_count > 10:
            complexity_score += 2
        elif word_count > 5:
            complexity_score += 1
        
        # Keyword-based complexity
        complex_keywords = [
            'impact', 'effect', 'analysis', 'comparison', 'history',
            'future', 'trends', 'challenges', 'opportunities', 'benefits',
            'risks', 'economic', 'social', 'political', 'environmental',
            'technology', 'development', 'evolution', 'implementation'
        ]
        
        for keyword in complex_keywords:
            if keyword in topic_lower:
                complexity_score += 1
        
        # Determine threshold
        if complexity_score >= 4:
            return 15  # Complex topic
        elif complexity_score >= 2:
            return 10  # Medium complexity
        else:
            return self.min_references_default  # Simple topic
    
    def _count_references(self, findings: str) -> int:
        """Count number of references/sources in findings."""
        # Look for markdown links
        links = re.findall(r'\[.*?\]\(https?://.*?\)', findings)
        
        # Also look for bare URLs
        urls = re.findall(r'https?://[^\s\)]+', findings)
        
        # Combine and deduplicate
        all_refs = set(links + urls)
        
        return len(all_refs)
    
    def _extract_sources(self, findings: str) -> List[str]:
        """Extract all source URLs from findings."""
        # Markdown links
        links = re.findall(r'\[.*?\]\(https?://.*?\)', findings)
        
        # Extract URLs from markdown
        urls = [re.search(r'\((https?://.*?)\)', link).group(1) for link in links 
                if re.search(r'\((https?://.*?)\)', link)]
        
        return urls
    
    def _get_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return None
    
    def _has_url_content(self, findings: str) -> bool:
        """Check if findings include actual URL content (not just links)."""
        # Look for substantial text content sections
        sections = re.split(r'\n\s*\n', findings)
        has_content = any(len(section) > 100 for section in sections)
        return has_content
    
    def _calculate_source_diversity(self, subagent_results: Dict[str, str]) -> float:
        """Calculate overall source diversity across all agents."""
        all_sources = []
        for findings in subagent_results.values():
            all_sources.extend(self._extract_sources(findings))
        
        if not all_sources:
            return 0.0
        
        domains = [self._get_domain(url) for url in all_sources]
        unique_domains = set(d for d in domains if d)
        
        if not unique_domains:
            return 0.0
        
        # Higher is better (more diverse)
        return len(unique_domains) / len(all_sources)
    
    def _calculate_content_quality(self, subagent_results: Dict[str, str]) -> float:
        """Calculate overall content quality score."""
        if not subagent_results:
            return 0.0
        
        total_quality = 0.0
        for findings in subagent_results.values():
            content_length = len(findings)
            # Quality based on length and structure
            quality = min(1.0, content_length / 2000)
            total_quality += quality
        
        return total_quality / len(subagent_results)
    
    def get_research_gaps(
        self,
        subagent_results: Dict[str, str],
        topic: str
    ) -> List[str]:
        """
        Identify gaps in research coverage.
        
        Args:
            subagent_results: Agent findings
            topic: Original topic
            
        Returns:
            List of suggested additional research areas
        """
        gaps = []
        
        # Check if certain aspects are missing
        topic_lower = topic.lower()
        
        if 'impact' in topic_lower or 'effect' in topic_lower:
            if not any(word in topic_lower for word in ['positive', 'negative', 'benefit', 'risk']):
                gaps.append("Consider researching both positive and negative impacts")
        
        if 'technology' in topic_lower or 'ai' in topic_lower:
            if 'ethics' not in topic_lower and 'ethical' not in topic_lower:
                gaps.append("Consider adding ethical implications research")
        
        if 'future' not in topic_lower and 'trend' not in topic_lower:
            gaps.append("Consider researching future trends and predictions")
        
        return gaps
