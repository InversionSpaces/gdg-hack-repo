import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QFileDialog, QTextEdit, 
                            QScrollArea, QLabel, QProgressDialog, QFrame, QTextBrowser,
                            QScrollArea, QVBoxLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyPDF2 import PdfReader, PdfWriter
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor
import fitz  # PyMuPDF
from PIL import Image
import io
from processing.document_processor import DocumentProcessor

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 128))  # Semi-transparent black
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Processing document...")

class ProcessingThread(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)

    def __init__(self, processor, content):
        super().__init__()
        self.processor = processor
        self.content = content

    def run(self):
        self.progress.emit("Processing document...")
        success, message = self.processor.process_document(self.content)
        self.finished.emit(success, message)

class AnswerThread(QThread):
    finished = pyqtSignal(dict, str)
    progress = pyqtSignal(str)

    def __init__(self, processor, question):
        super().__init__()
        self.processor = processor
        self.question = question

    def run(self):
        self.progress.emit("Getting answer...")
        result, status = self.processor.get_answer(self.question)
        self.finished.emit(result, status)

class PDFViewer(QWidget):
    def __init__(self, processor):
        super().__init__()
        self.current_page = 0
        self.base_pdf = None
        self.displaying_pdf = None
        self.processor = processor
        self.processing_thread = None
        self.loading_overlay = LoadingOverlay(self)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        
        # File selection button
        self.select_button = QPushButton("Select Files")
        self.select_button.clicked.connect(self.select_files)
        layout.addWidget(self.select_button)
        
        # PDF display area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.pdf_label = QLabel()
        self.scroll_area.setWidget(self.pdf_label)
        layout.addWidget(self.scroll_area)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_page)
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
        
        # Set up loading overlay
        self.loading_overlay.resize(self.size())
        self.loading_overlay.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.resize(self.size())

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "", 
            "All Supported Files (*.pdf *.jpg *.jpeg *.png *.txt);;PDF Files (*.pdf);;Image Files (*.jpg *.jpeg *.png);;Text Files (*.txt)"
        )
        if files:
            self.combine_files(files)

    def combine_files(self, files):
        progress = QProgressDialog("Processing files...", "Cancel", 0, len(files), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        self.base_pdf = fitz.open()
        
        for i, file_path in enumerate(files):
            if progress.wasCanceled():
                break
                
            progress.setValue(i)
            progress.setLabelText(f"Processing {os.path.basename(file_path)}...")
            
            try:
                if file_path.lower().endswith(('.pdf')):
                    doc = fitz.open(file_path)
                    self.base_pdf.insert_pdf(doc)
                    doc.close()
                    
                elif file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img = Image.open(file_path)
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format='PDF')
                    img_doc = fitz.open(stream=img_bytes.getvalue(), filetype="pdf")
                    self.base_pdf.insert_pdf(img_doc)
                    img_doc.close()
                    
                elif file_path.lower().endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    
                    page = self.base_pdf.new_page()
                    page.insert_text((50, 50), text)
                    
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
        
        progress.setValue(len(files))
        
        if self.base_pdf.page_count > 0:
            self.current_page = 0
            self.displaying_pdf = self.base_pdf
            self.display_page()
            
            # Process the combined PDF in a background thread
            self.process_combined_pdf()

    def process_combined_pdf(self):
        if self.base_pdf:
            self.displaying_pdf = self.base_pdf

            # Show loading overlay
            self.loading_overlay.show()
            self.setEnabled(False)
            
            # Save the combined PDF to memory
            pdf_bytes = self.base_pdf.tobytes()
            
            # Start processing in background thread
            self.processing_thread = ProcessingThread(self.processor, pdf_bytes)
            self.processing_thread.progress.connect(self.update_progress)
            self.processing_thread.finished.connect(self.processing_finished)
            self.processing_thread.start()

    def update_progress(self, message):
        print(f"Progress: {message}")

    def processing_finished(self, success, message):
        # Hide loading overlay and re-enable the widget
        self.loading_overlay.hide()
        self.setEnabled(True)
        
        if success:
            print("Document processed successfully")
        else:
            print(f"Error: {message}")

    def display_page(self):
        if self.displaying_pdf and 0 <= self.current_page < len(self.displaying_pdf):
            page = self.displaying_pdf[self.current_page]
            pix = page.get_pixmap()
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            self.pdf_label.setPixmap(pixmap.scaled(
                self.scroll_area.size(), Qt.AspectRatioMode.KeepAspectRatio
            ))

    def prev_page(self):
        if self.displaying_pdf and self.current_page > 0:
            self.current_page -= 1
            self.display_page()

    def next_page(self):
        if self.displaying_pdf and self.current_page < len(self.displaying_pdf) - 1:
            self.current_page += 1
            self.display_page()

    def create_highlighted_pdf(self, relevant_paragraphs, selected_paragraph = None):
        """Create a new PDF with highlighted relevant paragraphs"""
        if not self.base_pdf:
            return False

        # Create a copy of the current PDF
        highlighted_pdf = fitz.open()
        highlighted_pdf.insert_pdf(self.base_pdf)

        # Draw bounding boxes for relevant paragraphs
        for paragraph in relevant_paragraphs:
            pdf_page = highlighted_pdf[paragraph.page_number]
            
            # Get page dimensions
            width = pdf_page.rect.width
            height = pdf_page.rect.height

            points = [(p[0] * width, p[1] * height) for p in paragraph.points]
                    
            # Draw the polygon with a semi-transparent yellow fill
            # First draw the fill
            # Then draw the border
            pdf_page.draw_polyline(points + [points[0]], color=(1, 0, 0), width=5.0)

        if selected_paragraph:
            pdf_page = highlighted_pdf[selected_paragraph.page_number]
            width = pdf_page.rect.width
            height = pdf_page.rect.height
            points = [(p[0] * width, p[1] * height) for p in selected_paragraph.points]
            pdf_page.draw_polyline(points + [points[0]], color=(0, 0, 1), fill=(0, 0, 1), fill_opacity=0.3)

        self.displaying_pdf = highlighted_pdf

        return True

    def display_highlighted_pdf(self, relevant_paragraphs, selected_paragraph = None):
        """Display the PDF with highlighted relevant paragraphs"""

        if self.create_highlighted_pdf(relevant_paragraphs, selected_paragraph):
            self.display_page()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.processor = DocumentProcessor()
        self.answer_thread = None
        self.current_paragraphs = []  # Store current paragraphs for navigation
        self.initUI()
        
        # Apply modern Material Design-inspired styles
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #1976D2;
            }
            
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
            
            QTextEdit, QTextBrowser {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #2196F3;
                selection-color: white;
            }
            
            QScrollArea {
                border: none;
                background-color: white;
            }
            
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            
            QLabel {
                color: #424242;
            }
            
            QProgressDialog {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            
            QProgressBar {
                border: 1px solid #E0E0E0;
                border-radius: 2px;
                text-align: center;
            }
            
            QProgressBar::chunk {
                background-color: #2196F3;
            }

            /* Response area specific styles */
            QFrame#response_frame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }

            QTextBrowser#response_text {
                background-color: white;
                border: none;
                border-radius: 0;
                padding: 12px;
            }

            QScrollArea#response_scroll {
                background-color: white;
                border: none;
            }

            QWidget#response_container {
                background-color: white;
            }
        """)

    def initUI(self):
        self.setWindowTitle('Notes Reader')
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create left panel for PDF viewer
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self.pdf_viewer = PDFViewer(self.processor)
        left_layout.addWidget(self.pdf_viewer)
        main_layout.addWidget(left_panel, 2)  # Takes 2/3 of the space

        # Create right panel for request/response
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Request input area
        request_frame = QFrame()
        request_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        request_layout = QVBoxLayout(request_frame)
        request_layout.setSpacing(4)  # Reduce spacing between widgets
        request_layout.setContentsMargins(4, 4, 4, 4)  # Reduce margins
        
        self.request_input = QTextEdit()
        request_layout.addWidget(self.request_input)
        
        self.send_button = QPushButton("Ask")
        self.send_button.setFixedHeight(30)  # Make button smaller
        self.send_button.setEnabled(False)  # Initially disabled
        self.send_button.clicked.connect(self.process_request)
        request_layout.addWidget(self.send_button)
        
        # Connect text changed signal to update button state
        self.request_input.textChanged.connect(self.update_send_button_state)
        
        right_layout.addWidget(request_frame)
        
        # Response area
        response_frame = QFrame()
        response_frame.setObjectName("response_frame")
        response_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        response_layout = QVBoxLayout(response_frame)
        
        response_label = QLabel("Response:")
        response_layout.addWidget(response_label)
        
        # Create a scroll area for the response text
        response_scroll = QScrollArea()
        response_scroll.setObjectName("response_scroll")
        response_scroll.setWidgetResizable(True)
        response_scroll.setFrameShape(QFrame.Shape.NoFrame)
        response_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create a container widget for the response content
        response_container = QWidget()
        response_container.setObjectName("response_container")
        response_container_layout = QVBoxLayout(response_container)
        response_container_layout.setContentsMargins(0, 0, 0, 0)
        response_container_layout.setSpacing(5)
        
        # Response text
        self.response_text = QTextBrowser()
        self.response_text.setObjectName("response_text")
        self.response_text.setReadOnly(True)
        self.response_text.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        response_container_layout.addWidget(self.response_text)
        
        # Paragraph buttons container
        self.paragraph_buttons_container = QWidget()
        self.paragraph_buttons_layout = QVBoxLayout(self.paragraph_buttons_container)
        self.paragraph_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.paragraph_buttons_layout.setSpacing(2)  # Reduce spacing between buttons
        response_container_layout.addWidget(self.paragraph_buttons_container)
        
        response_scroll.setWidget(response_container)
        response_layout.addWidget(response_scroll)
        
        right_layout.addWidget(response_frame)
        
        main_layout.addWidget(right_panel, 1)  # Takes 1/3 of the space

        # Create loading overlay for answer processing
        self.answer_loading_overlay = LoadingOverlay(self.response_text)
        self.answer_loading_overlay.hide()

    def update_send_button_state(self):
        """Update the send button state based on document and question input"""
        has_document = self.processor.has_document()
        has_question = bool(self.request_input.toPlainText().strip())
        self.send_button.setEnabled(has_document and has_question)

    def process_request(self):
        question = self.request_input.toPlainText().strip()
        if question and self.processor.has_document():
            # Disable input and show loading
            self.request_input.setEnabled(False)
            self.send_button.setEnabled(False)
            self.answer_loading_overlay.show()
            
            # Start processing in background thread
            self.answer_thread = AnswerThread(self.processor, question)
            self.answer_thread.progress.connect(self.update_answer_progress)
            self.answer_thread.finished.connect(self.answer_finished)
            self.answer_thread.start()

    def update_answer_progress(self, message):
        print(f"Progress: {message}")

    def clear_paragraph_buttons(self):
        """Clear all paragraph buttons"""
        while self.paragraph_buttons_layout.count():
            item = self.paragraph_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add a styled label for the paragraph list
        paragraph_label = QLabel("Relevant Information")
        paragraph_label.setStyleSheet("""
            QLabel {
                color: #424242;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 0 8px 0;
            }
        """)
        self.paragraph_buttons_layout.addWidget(paragraph_label)

    def create_paragraph_button(self, paragraph):
        """Create a button for a paragraph"""
        relevance = paragraph.relevance
        button = QPushButton()
        button.setMinimumHeight(50)  # Increased height for better touch targets
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QHBoxLayout(button)
        layout.setContentsMargins(12, 8, 12, 8)  # Increased padding
        layout.setSpacing(8)  # Added spacing between elements
        
        # Create relevance indicator
        relevance_indicator = QLabel()
        relevance_indicator.setFixedSize(8, 8)
        relevance_indicator.setStyleSheet("""
            background-color: #2196F3;
            border-radius: 4px;
        """)
        layout.addWidget(relevance_indicator)
        
        # Create text label
        label = QLabel(f"Page {paragraph.page_number + 1} • Relevance: {relevance}")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet("""
            color: #424242;
            font-size: 14px;
        """)
        layout.addWidget(label)
        
        # Add arrow icon
        arrow = QLabel("→")
        arrow.setStyleSheet("""
            color: #757575;
            font-size: 16px;
        """)
        layout.addWidget(arrow)
        
        button.setStyleSheet("""
            QPushButton {
                text-align: left;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
                margin: 4px 0;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
                border-color: #BDBDBD;
            }
            QPushButton:pressed {
                background-color: #EEEEEE;
            }
        """)
        button.clicked.connect(lambda checked, p=paragraph: self.handle_paragraph_click(p))
        return button

    def handle_paragraph_click(self, paragraph):
        """Handle clicks on paragraph buttons to navigate to the corresponding page"""
        self.pdf_viewer.display_highlighted_pdf(self.current_paragraphs, paragraph)
        self.pdf_viewer.current_page = paragraph.page_number
        self.pdf_viewer.display_page()

    def answer_finished(self, result, status):
        # Hide loading overlay and re-enable input
        self.answer_loading_overlay.hide()
        self.request_input.setEnabled(True)
        self.update_send_button_state()
        
        if result:
            response = result["answer"]
            self.current_paragraphs = result["paragraphs"]
            
            # Display the PDF with highlighted relevant paragraphs
            self.pdf_viewer.display_highlighted_pdf(self.current_paragraphs)
            
            # Set the answer text
            self.response_text.setPlainText(response)
            
            # Clear existing paragraph buttons
            self.clear_paragraph_buttons()
            
            # Create buttons for each paragraph
            for paragraph in self.current_paragraphs:
                button = self.create_paragraph_button(paragraph)
                self.paragraph_buttons_layout.addWidget(button)
            
            # Add a stretch to push buttons to the top
            self.paragraph_buttons_layout.addStretch()
        else:
            self.response_text.setPlainText(f"Error: {status}")
            self.clear_paragraph_buttons()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()