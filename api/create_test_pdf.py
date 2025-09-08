#!/usr/bin/env python3
"""
Create a simple valid PDF file for testing
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_test_pdf() -> Path:
    """Create a simple test PDF file"""
    pdf_path = Path("/Users/feihe/Workspace/slide-speaker/api/test_valid.pdf")

    # Create a PDF with ReportLab
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter

    # Add some content
    c.setFont("Helvetica", 16)
    c.drawString(100, height - 100, "Test PDF Document")

    c.setFont("Helvetica", 12)
    c.drawString(100, height - 150, "This is a simple test PDF file for processing.")
    c.drawString(
        100, height - 170, "It contains some basic text content that can be analyzed."
    )
    c.drawString(
        100,
        height - 190,
        "The PDF processing pipeline should be able to read this content.",
    )

    # Add a second page
    c.showPage()
    c.setFont("Helvetica", 16)
    c.drawString(100, height - 100, "Second Page")

    c.setFont("Helvetica", 12)
    c.drawString(100, height - 150, "This is the second page of the test document.")
    c.drawString(100, height - 170, "It contains additional content for segmentation.")

    # Add a third page
    c.showPage()
    c.setFont("Helvetica", 16)
    c.drawString(100, height - 100, "Third Page")

    c.setFont("Helvetica", 12)
    c.drawString(100, height - 150, "This is the third page of the test document.")
    c.drawString(
        100,
        height - 170,
        "It provides enough content for the AI to analyze and segment.",
    )

    # Save the PDF
    c.save()

    print(f"Created test PDF at: {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    create_test_pdf()
