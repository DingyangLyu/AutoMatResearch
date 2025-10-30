"""
Simple Multi-Keyword Query Generator
User-defined keywords with AND/OR logic selection
"""

import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleQueryGenerator:
    """Simple query generator for user-defined keywords"""

    def __init__(self):
        pass

    def generate_query(self, keywords: List[str], logic: str = "AND",
                      search_fields: List[str] = None,
                      categories: List[str] = None) -> str:
        """
        Generate query from multiple keywords with user-specified logic

        Args:
            keywords: List of keywords
            logic: "AND" or "OR" logic
            search_fields: Fields to search ['all', 'ti', 'au', 'abs', 'cat']
            categories: arXiv categories to include

        Returns:
            Generated arXiv query string
        """
        if not keywords:
            return ""

        # Default settings
        if not search_fields:
            search_fields = ['all']
        if not categories:
            categories = []

        # Clean keywords
        clean_keywords = [self._clean_keyword(kw) for kw in keywords if kw and kw.strip()]

        if not clean_keywords:
            return ""

        # Build query parts
        query_parts = []

        # Add category restrictions if specified
        if categories:
            category_part = ' OR '.join([f'cat:{cat}' for cat in categories])
            if len(categories) > 1:
                query_parts.append(f'({category_part})')
            else:
                query_parts.append(category_part)

        # Add keywords with specified logic
        keyword_parts = []
        for keyword in clean_keywords:
            for field in search_fields:
                if len(keyword.split()) > 1:  # Multi-word phrase
                    keyword_parts.append(f'{field}:"{keyword}"')
                else:  # Single word
                    keyword_parts.append(f'{field}:{keyword}')

        # Combine keywords with logic
        if keyword_parts:
            logic_operator = f' {logic} '
            combined_keywords = logic_operator.join(keyword_parts)

            # Wrap in parentheses if multiple keywords and there are categories
            if len(keyword_parts) > 1 and query_parts:
                query_parts.append(f'({combined_keywords})')
            else:
                query_parts.append(combined_keywords)

        # Combine all parts with AND logic (categories AND keywords)
        final_query = ' AND '.join(query_parts)

        logger.info(f"Generated simple query: {final_query}")
        return final_query

    def _clean_keyword(self, keyword: str) -> str:
        """Clean individual keyword"""
        # Remove extra spaces
        cleaned = re.sub(r'\s+', ' ', keyword.strip())

        # Keep only alphanumeric and common characters
        cleaned = re.sub(r'[^\w\s\-\.,\'"()]', ' ', cleaned)

        return cleaned

    def generate_arxiv_query(self, keywords: List[str], logic: str = "AND",
                           use_categories: bool = False,
                           category_fields: List[str] = None) -> str:
        """
        Generate arXiv-specific query

        Args:
            keywords: List of keywords
            logic: "AND" or "OR" logic
            use_categories: Whether to include arXiv categories (default: False)
            category_fields: Specific categories to include

        Returns:
            arXiv query string
        """
        # Only use categories if explicitly requested and provided
        if use_categories and category_fields:
            search_fields = ['all']
            return self.generate_query(
                keywords=keywords,
                logic=logic,
                search_fields=search_fields,
                categories=category_fields
            )
        else:
            # Default: only use keywords, no categories
            search_fields = ['all']
            return self.generate_query(
                keywords=keywords,
                logic=logic,
                search_fields=search_fields,
                categories=None
            )

    def get_query_examples(self) -> Dict[str, List[str]]:
        """Get example keyword combinations"""
        return {
            "Materials Science": [
                ["materials science", "crystal structure", "property prediction"],
                ["perovskite", "solar cells", "photovoltaic"],
                ["graphene", "2D materials", "electronic properties"]
            ],
            "Machine Learning": [
                ["deep learning", "neural networks", "training"],
                ["machine learning", "prediction", "algorithms"],
                ["artificial intelligence", "automation", "optimization"]
            ],
            "Interdisciplinary": [
                ["materials science", "machine learning", "discovery"],
                ["computational materials", "AI", "high-throughput"],
                ["deep learning", "materials", "property prediction"]
            ]
        }

    def explain_query(self, query: str) -> str:
        """Explain the generated query"""
        if not query:
            return "Empty query"

        explanation_parts = []

        if "AND" in query:
            explanation_parts.append("• Uses AND logic: All terms must be present")
        if "OR" in query:
            explanation_parts.append("• Uses OR logic: Any term can be present")
        if "cat:" in query:
            explanation_parts.append("• Includes arXiv category restrictions")
        if 'all:"' in query:
            explanation_parts.append("• Searches for exact phrases")
        if "ti:" in query:
            explanation_parts.append("• Searches in titles")
        if "abs:" in query:
            explanation_parts.append("• Searches in abstracts")

        return '\n'.join(explanation_parts) if explanation_parts else "• Basic keyword search"


# Global instance
simple_generator = SimpleQueryGenerator()


def generate_simple_query(keywords: List[str], logic: str = "AND") -> str:
    """
    Generate simple query from keywords

    Args:
        keywords: List of keywords
        logic: "AND" or "OR" logic

    Returns:
        Generated query string
    """
    return simple_generator.generate_arxiv_query(keywords=keywords, logic=logic)


def get_query_examples() -> Dict[str, List[str]]:
    """Get example keyword combinations"""
    return simple_generator.get_query_examples()


def explain_generated_query(query: str) -> str:
    """Explain the generated query"""
    return simple_generator.explain_query(query)