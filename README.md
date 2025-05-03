# Notes Reader - GDG Hackathon 2025 Solution

A powerful document analysis and question-answering application built with PyQt6 and Google Cloud AI services. This application allows users to upload documents (PDF, images, text files) and ask questions about their content, with AI-powered responses and visual document navigation.

## Features

- 📄 Multi-format document support (PDF, JPG, JPEG, PNG, TXT)
- 🔍 Document text extraction and analysis
- ❓ AI-powered question answering
- 📑 Visual document navigation with highlighted relevant sections

## Google Cloud Setup

This application requires the following Google Cloud services and setup:

1. **Google Cloud Project**
   - Create a new project or use an existing one
   - Project ID: `gdg-hack-458611` (or update in `processing/config.py`)

2. **Required APIs**
   - Enable the following APIs in your Google Cloud Console:
     - Document AI API
     - Vertex AI API
     - Gemini API

3. **Service Account**
   - Create a service account with the following roles:
     - Document AI User
     - Vertex AI User
   - Download the service account key as JSON
   - Save it as `key.json` in the project root directory

4. **Document AI Processor**
   - Create a Document AI processor in the EU region
   - Update the `OCR_PROCESSOR_ID` in `processing/config.py` with your processor ID

5. **Environment Variables**
   - Set the following environment variables:
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
     export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value core/project)
     ```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/InversionSpaces/gdg-hack-repo
   cd gdg-hack-repo
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the application:
   ```bash
   python main.py
   ```

2. Upload documents using the "Select Files" button
3. Ask questions about the document content in the input field
4. View answers and navigate through relevant document sections

## Demo Video

[demo.mp4](./demo.mp4)

## Architecture

The application consists of several key components:

- **Document Processing**: Uses Google Cloud Document AI for text extraction and analysis
- **Question Answering**: Leverages Gemini AI for intelligent responses
- **UI Framework**: Built with PyQt6 for a modern, responsive interface
- **Background Processing**: Implements QThread for non-blocking operations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Cloud Platform
- PyQt6
- Google AI Services (Document AI, Vertex AI, Gemini) 