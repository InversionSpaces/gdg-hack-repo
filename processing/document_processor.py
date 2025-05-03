import json
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from google import genai
from google.genai.types import Content, GenerateContentConfig, Part
import vertexai
from processing.utils import *
from processing.config import *

vertexai.init(project=PROJECT_ID, location=VERTEXAI_LOCATION)

class DocumentProcessor:
    def __init__(self):
        # Initialize Document AI client
        self.docai_client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
        )
        
        # Initialize Vertex AI
        # self.embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_ID)
        
        # Initialize Gemini client
        self.gemini_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=VERTEXAI_LOCATION,
        )
        
        self.current_document = None
        self.paragraphs = []
        # self.embeddings = []

    def has_document(self):
        return self.current_document is not None

    def process_document(self, content):
        """Process a document and extract its text and structure."""
        try:
            # Load Binary Data into Document AI RawDocument Object
            raw_document = documentai.RawDocument(content=content, mime_type="application/pdf")

            # Configure the process request
            resource_name = self.docai_client.processor_path(
                PROJECT_ID, LOCATION, OCR_PROCESSOR_ID
            )   
            request = documentai.ProcessRequest(name=resource_name, raw_document=raw_document)

            # Process the document
            result = self.docai_client.process_document(request=request)
            self.current_document = result.document
            
            # Extract paragraphs
            self.paragraphs = get_paragraphs(self.current_document)
            
            # Generate embeddings for paragraphs
            # if self.paragraphs:
            #     self.embeddings = request_embeddings(self.embedding_model, self.paragraphs)
            
            return True, "Document processed successfully"
            
        except Exception as e:
            return False, f"Error processing document: {str(e)}"

    def get_document_text(self):
        """Get the full text of the processed document."""
        if self.current_document:
            return self.current_document.text
        return ""

    def get_paragraphs(self):
        """Get the extracted paragraphs from the document."""
        return self.paragraphs

    # def find_relevant_paragraphs(self, question, k=3):
    #     """Find the most relevant paragraphs for a given question."""
    #     if not self.paragraphs or not self.embeddings:
    #         return [], "No document processed yet"
            
    #     try:
    #         # Get embedding for the question
    #         question_embedding = request_embeddings(self.embedding_model, [question])[0]
            
    #         # Find k nearest paragraphs
    #         nearest_indices = find_k_nearest_embeddings(question_embedding, self.embeddings, k)
    #         relevant_paragraphs = [self.paragraphs[i] for i, _ in nearest_indices]
            
    #         return relevant_paragraphs, "Success"
            
    #     except Exception as e:
    #         return [], f"Error finding relevant paragraphs: {str(e)}"

    def get_answer(self, question):
        """Get an answer to a question based on the document content."""
        if not self.has_document():
            return None, "No document processed yet"
            
        try:
            # Get response from Gemini
            response = self.get_gemini_response(question)
            
            # Extract relevant paragraphs based on the response
            paragraphs_ids = response.get("paragraphs_ids", [])
            relevant_paragraphs = [self.paragraphs[i] for i in paragraphs_ids]
            
            return {
                "answer": response.get("answer", ""),
                "relevant_paragraphs": relevant_paragraphs
            }, "Success"
            
        except Exception as e:
            return None, f"Error getting answer: {str(e)}"

    def clear_document(self):
        """Clear the current document and its associated data."""
        self.current_document = None
        self.paragraphs = []
        # self.embeddings = []

    def get_gemini_response(self, question: str):
        # Format the prompt with context and question
        
        context_str = '\n'.join([f"{i}: {paragraph.text}" for i, paragraph in enumerate(self.paragraphs)])
        
        print("Context:")
        print(context_str)
        print("Question:")
        print(question)
        
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
        response = self.gemini_client.models.generate_content(
            model=ANSWER_MODEL_ID, 
            contents=contents,
            config=generate_content_config
        )

        return json.loads(response.text)

    