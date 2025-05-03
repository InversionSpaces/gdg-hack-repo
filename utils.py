from typing import List
import fitz
from google.cloud.documentai_v1.types import Document
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
from google import genai
from google.genai.types import Content, GenerateContentConfig, Part
import time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import ANSWER_MODEL_ID

def get_paragraphs(document: Document):
    paragraphs = []
    for page in document.pages:
        for paragraph in page.paragraphs:
            anchor = paragraph.layout.text_anchor
            segments = anchor.text_segments
            text = ""
            for segment in segments:
                text += document.text[segment.start_index:segment.end_index]
            paragraphs.append(text)
    return paragraphs

def request_embeddings(model: TextEmbeddingModel, texts: List[str]):
    embeddings = []
    BATCH_SIZE = 32
    for i in range(0, len(texts), BATCH_SIZE):
        inputs = [TextEmbeddingInput(text=text, task_type="QUESTION_ANSWERING") for text in texts[i : i + BATCH_SIZE]]
        while True:
            try:
                embeddings.extend(model.get_embeddings(inputs))
                break
            except Exception as e:
                print(f"Error processing paragraph: {e}")
                time.sleep(10)

    return embeddings


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

def find_k_nearest_embeddings(query_embedding, paragraph_embeddings, k=3):
    """Find k nearest embeddings to the query embedding using cosine similarity."""
    similarities = []
    for i, p_embedding in enumerate(paragraph_embeddings):
        similarity = cosine_similarity(
            np.array(query_embedding.values).reshape(1, -1),
            np.array(p_embedding.values).reshape(1, -1)
        )[0][0]
        similarities.append((i, similarity))
    
    # Sort by similarity and get top k
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:k]

def get_gemini_response(client: genai.Client, question: str, context_paragraphs: List[str]) -> str:
    """Get response from Gemini model using the question and context paragraphs."""
    # Format the prompt with context and question
    
    context_str = '\n'.join([f"{i}: {paragraph}" for i, paragraph in enumerate(context_paragraphs)])
    systemInstruction = Content(
        parts=[
            Part.from_text(text="Provided context:"),
            Part.from_text(text=context_str),
            Part.from_text(text="Answer the question based on the context provided. " +
                           "Return the answer and the paragraphs ids that are relevant to the answer." +
                           "If there is no answer, state that you don't know and return an empty array of paragraphs ids.")
        ]
    )
    contents = [
        Content(
            role="user",
            parts=[Part.from_text(text=question)]
        )
    ]
    generate_content_config = GenerateContentConfig(
        temperature = 1,
        top_p = 0.95,
        max_output_tokens = 8192,
        response_modalities = ["TEXT"],
        system_instruction=systemInstruction,
        response_mime_type = "application/json",
        response_schema = {"type":"OBJECT","properties":{"answer":{"type":"STRING"},"paragraphs_ids":{"type":"ARRAY","items":{"type":"INTEGER"}}}}
    ) 
    response = client.models.generate_content(
        model=ANSWER_MODEL_ID, 
        contents=contents,
        config=generate_content_config
    )

    return response.text