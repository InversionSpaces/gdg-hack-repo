import json
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from google import genai
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextGenerationModel

from utils import *
from config import *

# The local file in your current working directory
FILE_PATH = "sample.pdf"
# Refer to https://cloud.google.com/document-ai/docs/file-types
# for supported file types
MIME_TYPE = "application/pdf"

# Instantiates a client
docai_client = documentai.DocumentProcessorServiceClient(
    client_options=ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
)

# Read the file into memory
with open(FILE_PATH, "rb") as image:
    image_content = image.read()

# Load Binary Data into Document AI RawDocument Object
raw_document = documentai.RawDocument(content=image_content, mime_type=MIME_TYPE)

# Configure the process request
RESOURCE_NAME = docai_client.processor_path(PROJECT_ID, LOCATION, OCR_PROCESSOR_ID)
request = documentai.ProcessRequest(name=RESOURCE_NAME, raw_document=raw_document)

# Use the Document AI client to process the sample form
result = docai_client.process_document(request=request)

document_object = result.document
print("Document processing complete.")
print(f"Text: {document_object.text}")

paragraphs = get_paragraphs(document_object)

question = "What is the bachelor degree of the person in the document?"

vertexai.init(project=PROJECT_ID, location="europe-west1")

model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_ID)

embeddings = request_embeddings(model, [question] + paragraphs)
qembedding, *pembeddings = embeddings

# Find k nearest paragraphs to the question
# k = 3  # Number of most relevant paragraphs to use
# nearest_indices = find_k_nearest_embeddings(qembedding, pembeddings, k)
# relevant_paragraphs = [paragraphs[i] for i, _ in nearest_indices]

# print(relevant_paragraphs)

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="europe-west1",
)

# Get response from Gemini
response = get_gemini_response(client, question, paragraphs)
print("\nQuestion:", question)
print("\nAnswer:", response)

response_json = json.loads(response)
paragraphs_ids = response_json["paragraphs_ids"]

print("Relevant paragraphs:")
for paragraph_id in paragraphs_ids:
    print(paragraphs[paragraph_id])

# draw_polygons_on_pdf(FILE_PATH, "output.pdf", document_object)
