import sys
import subprocess
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QTextEdit, QLineEdit, QPushButton, QScrollArea,
                             QLabel, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QTextCursor, QIcon

class ChatMessage:
    def __init__(self, text, is_user=True, timestamp=None):
        self.text = text
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now()

class ChatBot:
    
    def __init__(self, timeout_seconds=120):
        self.model_name = "llama3.2"
        self.timeout_seconds = timeout_seconds 
        self.test_ollama()
    
    def test_ollama(self):
        """Test if Ollama is properly installed and accessible"""
        try:
            result = subprocess.run(["ollama", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"Ollama version: {result.stdout.strip()}")
            else:
                print("Warning: Ollama command failed")
        except Exception as e:
            print(f"Warning: Could not test Ollama - {e}")
    
    def check_model(self):
        """Check if the Llama model is available"""
        try:
            result = subprocess.run(["ollama", "list"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                if self.model_name in result.stdout:
                    return True
                else:
                    print(f"Warning: Model {self.model_name} not found in available models")
                    return False
        except Exception as e:
            print(f"Warning: Could not check models - {e}")
            return False
    
    def get_response(self, user_message):
        """Generate a response using the Llama model"""
        try:
            # Check if model is available first
            if not self.check_model():
                return f"Error: Model '{self.model_name}' is not available. Please run 'ollama pull {self.model_name}' to download it."
            
            # API
            try:
                import requests
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": user_message,
                        "stream": False
                    },
                                         timeout=self.timeout_seconds 
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'response' in result:
                        return result['response'].strip()
                    else:
                        print(f"API response: {result}")
                        return "Received unexpected response format from Llama API."
                else:
                    print(f"API error: {response.status_code} - {response.text}")
                    # Fall back to subprocess method
                    
            except ImportError:
                print("requests module not available, using subprocess method")
            except Exception as api_error:
                print(f"API method failed: {api_error}, trying subprocess method")
            
            process = subprocess.Popen(
                ["ollama", "run", self.model_name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate(input=user_message + "\n", timeout=self.timeout_seconds)  
            
            
            if process.returncode != 0:
                error_msg = stderr.strip() if stderr else "Unknown error"
                return f"Error running Llama model: {error_msg}"
            
            response = stdout.strip()
            
            if not response:
                return "I'm sorry, I couldn't generate a response right now. Please try again."
            
            return response
            
        except subprocess.TimeoutExpired:
            timeout_minutes = self.timeout_seconds // 60
            return f"The request is taking longer than expected (over {timeout_minutes} minutes). This can happen with complex or very long prompts. You can try:\n\n1. Breaking your question into smaller parts\n2. Waiting a bit longer and trying again\n3. Using a shorter, more specific prompt"
        except FileNotFoundError:
            return "Error: Ollama is not installed or not found in PATH. Please install Ollama first."
        except Exception as e:
            return f"I encountered an error: {str(e)}. Please try again."

class ChatWorker(QThread):
    response_ready = pyqtSignal(str)
    
    def __init__(self, chatbot):
        super().__init__()
        self.chatbot = chatbot
        self.user_message = ""
    
    def process_message(self, message):
        self.user_message = message
        self.start()
    
    def run(self):
        self.msleep(500)
        response = self.chatbot.get_response(self.user_message)
        self.response_ready.emit(response)

class MessageWidget(QWidget):
    """Widget to display individual chat messages"""
    
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.message = message
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        # message bubble
        message_frame = QFrame()
        message_frame.setFrameStyle(QFrame.Box)
        message_frame.setLineWidth(1)
        
        if self.message.is_user:
            message_frame.setStyleSheet("""
                QFrame {
                    background-color: #2C3E50;
                    border: 1px solid #34495E;
                    border-radius: 15px;
                    padding: 8px;
                }
            """)
            layout.addStretch()
        else:
            message_frame.setStyleSheet("""
                QFrame {
                    background-color: #ECF0F1;
                    border: 1px solid #BDC3C7;
                    border-radius: 15px;
                    padding: 8px;
                }
            """)
        
        # Message text
        message_text = QLabel(self.message.text)
        message_text.setWordWrap(True)
        message_text.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        if self.message.is_user:
            message_text.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 14px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
            """)
        
        # Timestamp
        timestamp = QLabel(self.message.timestamp.strftime("%H:%M"))
        timestamp.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        # Layout for message content
        message_layout = QVBoxLayout()
        message_layout.addWidget(message_text)
        message_layout.addWidget(timestamp, alignment=Qt.AlignRight)
        
        message_frame.setLayout(message_layout)
        layout.addWidget(message_frame)
        
        if not self.message.is_user:
            layout.addStretch()
        
        self.setLayout(layout)

class ChatbotUI(QMainWindow):
    """Main chatbot application window"""
    
    def __init__(self):
        super().__init__()
        self.chatbot = ChatBot()
        self.chat_worker = ChatWorker(self.chatbot)
        self.messages = []
        self.generating_widget = None
        self.typing_timer = None
        self.setup_ui()
        self.setup_connections()
        
        #welcome message
        self.add_message("Hello! I'm LlamaBot powered by Llama 3.2. How can I help you today?", is_user=False)
    
    def setup_ui(self):
        self.setWindowTitle("LlamaBot Chat")
        self.setGeometry(100, 100, 800, 600)
        
        # Set window icon
        try:
            icon = QIcon("llama.png")
            self.setWindowIcon(icon)
        except Exception as e:
            print(f"Could not load window icon: {e}")
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Chat area
        self.chat_area = self.create_chat_area()
        main_layout.addWidget(self.chat_area)
        
        # Input area
        input_area = self.create_input_area()
        main_layout.addWidget(input_area)
    
    def create_header(self):
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QFrame {
                background-color: #2C3E50;
                border-bottom: 2px solid #34495E;
            }
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Title
        title = QLabel("LlamaBot (Llama 3.2)")
        title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        # Status indicator
        status = QLabel("● Online")
        status.setStyleSheet("""
            QLabel {
                color: #27AE60;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(status)
        
        return header
    
    def create_chat_area(self):
        # Scroll area for messages
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #FFFFFF;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #F8F9FA;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #BDC3C7;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #95A5A6;
            }
        """)
        
        # Widget to hold messages
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(5)
        self.messages_layout.addStretch()
        
        scroll_area.setWidget(self.messages_widget)
        return scroll_area
    
    def create_input_area(self):
        input_frame = QFrame()
        input_frame.setFixedHeight(80)
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-top: 1px solid #E9ECEF;
            }
        """)
        
        layout = QHBoxLayout(input_frame)
        layout.setContentsMargins(15, 10, 15, 15)
        layout.setSpacing(10)
        
        # Message input
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 2px solid #E9ECEF;
                border-radius: 20px;
                padding: 10px 15px;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #2C3E50;
            }
            QLineEdit:focus {
                border: 2px solid #3498DB;
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setFixedSize(80, 40)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: #FFFFFF;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #21618C;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        
        layout.addWidget(self.message_input)
        layout.addWidget(self.send_button)
        
        return input_frame
    
    def setup_connections(self):
        self.chat_worker.response_ready.connect(self.handle_bot_response)
    
    def send_message(self):
        message_text = self.message_input.text().strip()
        if not message_text:
            return
        
        # Add user message
        self.add_message(message_text, is_user=True)
        
        # Clear input
        self.message_input.clear()
        
        # Add "Generating..." message
        self.add_generating_message()
        
        # Process with chatbot
        self.chat_worker.process_message(message_text)
    
    def handle_bot_response(self, response):
        self.remove_generating_message()
    
        self.add_message(response, is_user=False)
    
    def add_message(self, text, is_user=True):
        message = ChatMessage(text, is_user)
        self.messages.append(message)
        
 
        message_widget = MessageWidget(message)
        
 
        self.messages_layout.insertWidget(len(self.messages) - 1, message_widget)
        
        #Scroll button
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        scroll_area = self.chat_area
        scrollbar = scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def add_generating_message(self):
        """Add a 'Generating...' message with typing indicator"""
        # generating message animation
        generating_text = "Generating..."
        self.generating_message = ChatMessage(generating_text, is_user=False)
        
        self.generating_widget = self.create_generating_widget()
        
        #layout
        self.messages_layout.insertWidget(len(self.messages), self.generating_widget)
        
        # Scroll to bottom
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def remove_generating_message(self):
        """Remove the 'Generating...' message"""
        if hasattr(self, 'generating_widget') and self.generating_widget:
            # Stop typing animation
            if hasattr(self, 'typing_timer'):
                self.typing_timer.stop()
                self.typing_timer.deleteLater()
            
            
            self.messages_layout.removeWidget(self.generating_widget)
            self.generating_widget.deleteLater()
            self.generating_widget = None
    
    def create_generating_widget(self):
        """Create a widget with typing animation"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Create message bubble
        message_frame = QFrame()
        message_frame.setStyleSheet("""
            QFrame {
                background-color: #ECF0F1;
                border: 1px solid #BDC3C7;
                border-radius: 15px;
                padding: 8px;
            }
        """)
        
        # Create typing indicator
        typing_layout = QHBoxLayout()
        typing_layout.setSpacing(4)
        
        # Add "Generating" text
        text_label = QLabel("Generating")
        text_label.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        typing_layout.addWidget(text_label)
        
        # Add animated dots
        self.typing_dots = []
        for i in range(3):
            dot = QLabel("•")
            dot.setStyleSheet("""
                QLabel {
                    color: #3498DB;
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
            typing_layout.addWidget(dot)
            self.typing_dots.append(dot)
        
        typing_layout.addStretch()
        
        message_frame.setLayout(typing_layout)
        layout.addWidget(message_frame)
        layout.addStretch()
        
        widget.setLayout(layout)
        
        self.start_typing_animation()
        
        return widget
    
    def start_typing_animation(self):
        """Start the typing dots animation"""
        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self.animate_typing_dots)
        self.typing_timer.start(500)  # Update every 500ms
        self.typing_dot_index = 0
    
    def animate_typing_dots(self):
        """Animate the typing dots"""
        if not hasattr(self, 'typing_dots') or not self.typing_dots:
            return
            
        for dot in self.typing_dots:
            dot.setStyleSheet("""
                QLabel {
                    color: #BDC3C7;
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
        
        if self.typing_dot_index < len(self.typing_dots):
            self.typing_dots[self.typing_dot_index].setStyleSheet("""
                QLabel {
                    color: #3498DB;
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
        
        # Move to next dot
        self.typing_dot_index = (self.typing_dot_index + 1) % len(self.typing_dots)
    
    def closeEvent(self, event):
        """Handle application close event"""
        if hasattr(self, 'typing_timer') and self.typing_timer:
            self.typing_timer.stop()
            self.typing_timer.deleteLater()
        
        event.accept()

def main():
    app = QApplication(sys.argv)

    app.setStyle('Fusion')
    
    window = ChatbotUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
