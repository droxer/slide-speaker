"""
Document processing package for SlideSpeaker.

This package handles document analysis and slide extraction for presentations.
"""

from .analyzer import PDFAnalyzer
from .extractor import SlideExtractor

__all__ = ["PDFAnalyzer", "SlideExtractor"]
