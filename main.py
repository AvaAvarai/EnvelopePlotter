import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QFileDialog
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QColor

from OpenGL.GL import *

import numpy as np
import pandas as pd


class OpenGLPlot(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = pd.DataFrame()
        self.classes = pd.Series()
        self.unique_classes = []
        self.colors = []
        
        # Additional storage for envelope minima and maxima
        self.envelope_min = pd.DataFrame()
        self.envelope_max = pd.DataFrame()

        self.show_envelope = False  # Initially set to not show the envelope

    def load_data(self, file_name):
        dataset = pd.read_csv(file_name)
        self.classes = dataset['class']
        self.data = dataset.drop(columns=['class'])
        
        self.dataset_name = file_name.split("/")[-1]  # Store just the filename
        
        # Combine the data and classes into a single DataFrame
        combined = pd.concat([self.data, self.classes], axis=1)
        
        # Sort the combined DataFrame by the class labels
        combined = combined.sort_values(by='class')
        
        # Split the sorted DataFrame back into data and classes
        self.classes = combined['class']
        self.data = combined.drop(columns=['class'])
        
        self.unique_classes = self.classes.unique()

        # Generate unique colors for each class
        self.colors = np.linspace(0.1, 0.9, len(self.unique_classes))
        
        # Compute minima and maxima for each class
        self.envelope_min = self.data.groupby(self.classes).min()
        self.envelope_max = self.data.groupby(self.classes).max()

        self.normalize_data()
        self.update()

    def normalize_data(self):
        min_val = self.data.min()
        max_val = self.data.max()

        self.data = (self.data - min_val) / (max_val - min_val)
        self.envelope_min = (self.envelope_min - min_val) / (max_val - min_val)
        self.envelope_max = (self.envelope_max - min_val) / (max_val - min_val)

    def get_color_for_class(self, class_label):
        idx = np.where(self.unique_classes == class_label)[0][0]
        return (self.colors[idx], 0.5, 1 - self.colors[idx])

    def initializeGL(self):
        glClearColor(0.85, 0.85, 0.85, 1)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def paintGL(self):
        glClearColor(0.85, 0.85, 0.85, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glDisable(GL_DEPTH_TEST)

        if self.data.empty:
            return

        num_axes = self.data.shape[1]

        # Define margins
        x_margin = 0.2
        y_margin = 0.1
        x_min = -1 + x_margin
        x_max = 1 - x_margin
        y_min = -1 + y_margin
        y_max = 1 - y_margin

        # Adjust axis_gap for x_margin
        axis_gap = (x_max - x_min) / (num_axes - 1)

        # Draw axes
        glColor3f(0, 0, 0)  # Black color for axes
        for i in range(num_axes):
            glBegin(GL_LINES)
            glVertex2f(x_min + i * axis_gap, y_min)
            glVertex2f(x_min + i * axis_gap, y_max)
            glEnd()

        # Start QPainter
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setPen(Qt.GlobalColor.black)
        font = painter.font()
        font.setPointSize(font.pointSize() - 1)  # Decrease font size by 1
        painter.setFont(font)

        # Positioning details
        start_x = 10
        start_y = 25
        rect_size = 15
        gap = 5

        painter.drawText(start_x, start_y - 10, self.dataset_name)
        for idx, class_label in enumerate(self.unique_classes):
            r, g, b = [int(c * 255) for c in self.get_color_for_class(class_label)]
            painter.setBrush(QColor(r, g, b))
            
            rect_x = int(start_x)
            rect_y = int(start_y + (rect_size + gap) * idx)
            painter.drawRect(rect_x, rect_y, rect_size, rect_size)

            label = f"{class_label} ({(self.classes == class_label).sum()})"
            text_x = int(start_x + rect_size + gap)
            
            text_rect = painter.fontMetrics().boundingRect(label)
            
            # Adjust the vertical positioning to be centered with the colored box
            text_y = rect_y + (rect_size - text_rect.height()) // 2 + text_rect.height() - 3
            
            painter.drawText(text_x, text_y, label)
        
        # Draw axes and attribute names
        attribute_names = self.data.columns.tolist()  # Get attribute names from the DataFrame
        for i, attribute_name in enumerate(attribute_names):
            glBegin(GL_LINES)
            glVertex2f(x_min + i * axis_gap, y_min)
            glVertex2f(x_min + i * axis_gap, y_max)
            glEnd()
            
            # Calculate the width of the text string
            text_width = painter.fontMetrics().horizontalAdvance(attribute_name)
            
            # Render attribute name below the axis using QPainter
            text_x = int((x_min + i * axis_gap) * self.width() * 0.5 + self.width() * 0.5 - text_width / 2)
            text_y = int(self.height() - 10)
            painter.drawText(text_x, text_y, attribute_name)

        # End QPainter
        painter.end()

        # Reset OpenGL states for drawing lines
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        
        glLineWidth(0.5)  # Set line width
        if not self.show_envelope:
            # Draw individual data lines
            for idx, row in self.data.iterrows():
                r, g, b = self.get_color_for_class(self.classes[idx])
                glColor4f(r, g, b, 0.5)
                glBegin(GL_LINE_STRIP)
                for i, value in enumerate(row):
                    glVertex2f(x_min + i * axis_gap, y_min + (y_max - y_min) * value)
                glEnd()
        else:
            # Draw the envelope
            for class_label in self.unique_classes:
                r, g, b = self.get_color_for_class(class_label)
                
                # Draw the shaded envelope area using triangles
                glColor4f(r, g, b, 0.2)  # Very slightly transparent for shading
                
                for i in range(self.data.shape[1] - 1):
                    # Define the four points for this segment of the envelope
                    top_left = (x_min + i * axis_gap, y_min + (y_max - y_min) * self.envelope_max.loc[class_label, self.data.columns[i]])
                    top_right = (x_min + (i + 1) * axis_gap, y_min + (y_max - y_min) * self.envelope_max.loc[class_label, self.data.columns[i + 1]])
                    bottom_left = (x_min + i * axis_gap, y_min + (y_max - y_min) * self.envelope_min.loc[class_label, self.data.columns[i]])
                    bottom_right = (x_min + (i + 1) * axis_gap, y_min + (y_max - y_min) * self.envelope_min.loc[class_label, self.data.columns[i + 1]])
                    
                    # Draw two triangles to form the shaded envelope for this segment
                    glBegin(GL_TRIANGLES)
                    glVertex2f(*top_left)
                    glVertex2f(*top_right)
                    glVertex2f(*bottom_left)
                    
                    glVertex2f(*bottom_left)
                    glVertex2f(*top_right)
                    glVertex2f(*bottom_right)
                    glEnd()
                
                # Draw the maximum envelope line
                glColor4f(r, g, b, 0.5)
                glBegin(GL_LINE_STRIP)
                for i in range(self.data.shape[1]):
                    glVertex2f(x_min + i * axis_gap, y_min + (y_max - y_min) * self.envelope_max.loc[class_label, self.data.columns[i]])
                glEnd()

                # Draw the minimum envelope line
                glColor4f(r, g, b, 0.5)
                glBegin(GL_LINE_STRIP)
                for i in range(self.data.shape[1]):
                    glVertex2f(x_min + i * axis_gap, y_min + (y_max - y_min) * self.envelope_min.loc[class_label, self.data.columns[i]])
                glEnd()

        glEnable(GL_DEPTH_TEST)


    def resizeGL(self, w, h):
        # Set the viewport to take up the full canvas
        glViewport(0, 0, w, h)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Parallel Envelope Plotter")
        self.setGeometry(0, 0, 1200, 625)
        self.center_on_screen()

        layout = QVBoxLayout()

        # Add OpenGL context
        self.opengl_widget = OpenGLPlot(self)
        layout.addWidget(self.opengl_widget)

        # Create the buttons
        self.load_csv_btn = QPushButton("Load CSV")
        self.load_csv_btn.clicked.connect(self.load_csv_file)
        self.toggle_envelope_btn = QPushButton("Toggle Envelope")
        self.toggle_envelope_btn.clicked.connect(self.toggle_envelope)

        # Create a horizontal layout for buttons
        button_layout = QHBoxLayout()

        # Add buttons to the horizontal layout and restrict their height
        self.load_csv_btn.setMaximumHeight(25)
        self.toggle_envelope_btn.setMaximumHeight(25)
        button_layout.addWidget(self.load_csv_btn)
        button_layout.addWidget(self.toggle_envelope_btn)

        # Add the horizontal layout to the main vertical layout
        layout.addLayout(button_layout)

        # Create a QWidget to set as the main window's central widget
        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def keyPressEvent(self, event):
        # Check for Escape key or Ctrl+W
        if event.key() == Qt.Key.Key_Escape or (event.key() == Qt.Key.Key_W and event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            self.close()

    def center_on_screen(self):
        """Center the window on the screen."""
        qt_rectangle = self.frameGeometry()
        center_point = QApplication.screens()[0].availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())
    
    def load_csv_file(self):
        options = QFileDialog.Option.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_name:
            # Load your CSV data here using file_name
            print(f"Loading {file_name}")
            self.opengl_widget.load_data(file_name)

    def toggle_envelope(self):
        self.opengl_widget.show_envelope = not self.opengl_widget.show_envelope
        self.opengl_widget.update()  # Refresh the OpenGL view


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
