import fitz
from google.cloud.documentai_v1.types import Document

# Load your processed Document AI response
def draw_polygons_on_pdf(input_pdf_path: str, output_pdf_path: str, document: Document):
    # Open the original PDF
    pdf_doc = fitz.open(input_pdf_path)

    for page_idx, page in enumerate(document.pages):
        pdf_page = pdf_doc[page_idx]

        # Get page dimensions from PyMuPDF
        width = pdf_page.rect.width
        height = pdf_page.rect.height

        # Draw bounding boxes for each paragraph (change to lines/tokens if needed)
        for paragraph in page.paragraphs:
            poly = paragraph.layout.bounding_poly
            points = [(v.x / page.dimension.width, v.y / page.dimension.height) for v in poly.vertices]
            points = [(p[0] * width, p[1] * height) for p in points]

            # Draw the polygon
            pdf_page.draw_polyline(points + [points[0]], color=(1, 0, 0), width=1.0)

    # Save the modified PDF
    pdf_doc.save(output_pdf_path)