import fitz
from google.cloud.documentai_v1.types import Document

class Paragraph:
    def __init__(self, text: str, layout):
        self.text = text
        self.layout = layout

def get_paragraphs(document: Document):
    paragraphs = []
    for page in document.pages:
        for paragraph in page.paragraphs:
            anchor = paragraph.layout.text_anchor
            segments = anchor.text_segments
            text = ""
            for segment in segments:
                text += document.text[segment.start_index:segment.end_index]
            paragraphs.append(Paragraph(text, paragraph.layout))
    return paragraphs

# def request_embeddings(model: TextEmbeddingModel, texts: List[str]):
#     embeddings = []
#     BATCH_SIZE = 32
#     for i in range(0, len(texts), BATCH_SIZE):
#         inputs = [TextEmbeddingInput(text=text, task_type="QUESTION_ANSWERING") for text in texts[i : i + BATCH_SIZE]]
#         while True:
#             try:
#                 embeddings.extend(model.get_embeddings(inputs))
#                 break
#             except Exception as e:
#                 print(f"Error processing paragraph: {e}")
#                 time.sleep(10)

#     return embeddings


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

# def find_k_nearest_embeddings(query_embedding, paragraph_embeddings, k=3):
#     """Find k nearest embeddings to the query embedding using cosine similarity."""
#     similarities = []
#     for i, p_embedding in enumerate(paragraph_embeddings):
#         similarity = cosine_similarity(
#             np.array(query_embedding.values).reshape(1, -1),
#             np.array(p_embedding.values).reshape(1, -1)
#         )[0][0]
#         similarities.append((i, similarity))
    
#     # Sort by similarity and get top k
#     similarities.sort(key=lambda x: x[1], reverse=True)
#     return similarities[:k]