from vertexai import rag
from vertexai.generative_models import GenerativeModel, Tool
import vertexai
from google.cloud import storage
import os

from config import PROJECT_ID, PROCESSOR_ID

LOCATION = "us-central1"

# The local file in your current working directory
FILE_PATH = "sample.pdf"
# Refer to https://cloud.google.com/document-ai/docs/file-types
# for supported file types
MIME_TYPE = "application/pdf"

# Google Cloud Storage bucket name
BUCKET_NAME = f"{PROJECT_ID}-rag-files"

# Initialize Vertex AI API once per session
print("Initializing Vertex AI API...")
vertexai.init(project=PROJECT_ID, location=LOCATION)
print("Vertex AI API initialized")

gcs_uri = "gs://gdg-hack-458611-rag-files/sample.pdf"
if not gcs_uri:
    # Upload file to Google Cloud Storage
    print("Uploading file to Google Cloud Storage...")
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    if not bucket.exists():
        bucket = storage_client.create_bucket(BUCKET_NAME, location=LOCATION)

    blob_name = os.path.basename(FILE_PATH)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(FILE_PATH)
    gcs_uri = f"gs://{BUCKET_NAME}/{blob_name}"
    print(f"File uploaded to: {gcs_uri}")
else:
    print("Using existing GCS URI: ", gcs_uri)

# Create RagCorpus
# Configure embedding model, for example "text-embedding-005".
embedding_model_config = rag.RagEmbeddingModelConfig(
    vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
        publisher_model="publishers/google/models/text-embedding-005"
    )
)

corpus_name = "projects/127984195966/locations/us-central1/ragCorpora/2305843009213693952"
if not corpus_name:
    print("Creating RagCorpus...")
    rag_corpus = rag.create_corpus(
        display_name=corpus_name,
        backend_config=rag.RagVectorDbConfig(
            rag_embedding_model_config=embedding_model_config
        ),
    )
    print("RagCorpus created, name: ", rag_corpus.name)
else:
    print("Getting RagCorpus...")
    rag_corpus = rag.get_corpus(corpus_name)
    print("RagCorpus found, name: ", rag_corpus.name)

print("Deleting files from RagCorpus...")
files = rag.list_files(corpus_name=rag_corpus.name)
for file in files:
    print("Deleting file: ", file.name)
    rag.delete_file(file.name, corpus_name=rag_corpus.name)
    print("File deleted")

parser_processor_name = f"projects/127984195966/locations/us/processors/{PROCESSOR_ID}"

print("Importing files to RagCorpus...")
result = rag.import_files(
    corpus_name=rag_corpus.name,
    paths=[gcs_uri],
    transformation_config = rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(
            chunk_size=512,  # Optional
            chunk_overlap=100,  # Optional
        ),
    ),
    max_embedding_requests_per_min=900,  # Optional
    parser=rag.OCRParserConfig(
        processor_name=parser_processor_name,
        max_parsing_requests_per_min=120,  # Optional
    )
)
print("Files imported to RagCorpus:")
print(result)
print(result.partial_failures_gcs_path)

question = "Quel est le nom du personne dans le document?"

# Direct context retrieval
rag_retrieval_config = rag.RagRetrievalConfig(
    top_k=10,  # Optional
    # filter=rag.Filter(vector_distance_threshold=0.5),  # Optional
)

print("Retrieving context...")
response = rag.retrieval_query(
    rag_resources=[
        rag.RagResource(
            rag_corpus=rag_corpus.name,
            # Optional: supply IDs from `rag.list_files()`.
            # rag_file_ids=["rag-file-1", "rag-file-2", ...],
        )
    ],
    text=question,
    rag_retrieval_config=rag_retrieval_config,
)
print("Context retrieved:")
print(response)
print(len(response.contexts.contexts))

# Enhance generation
# Create a RAG retrieval tool
rag_retrieval_tool = Tool.from_retrieval(
    retrieval=rag.Retrieval(
        source=rag.VertexRagStore(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=rag_corpus.name,  # Currently only 1 corpus is allowed.
                    # Optional: supply IDs from `rag.list_files()`.
                    # rag_file_ids=["rag-file-1", "rag-file-2", ...],
                )
            ],
            rag_retrieval_config=rag_retrieval_config,
        ),
    )
)

# Create a Gemini model instance
rag_model = GenerativeModel(
    model_name="gemini-2.0-flash-001", tools=[rag_retrieval_tool]
)

# Generate response
print("Generating response...")
response = rag_model.generate_content(question)
print("Response generated:")
print(response.text)