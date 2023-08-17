import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QFileDialog
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt
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

    def load_data(self, file_name):
        dataset = pd.read_csv(file_name)
        self.classes = dataset['class']
        self.data = dataset.drop(columns=['class'])
        self.unique_classes = self.classes.unique()

        # Generate unique colors for each class
        self.colors = np.linspace(0.1, 0.9, len(self.unique_classes))

        self.normalize_data()
        self.update()

    def normalize_data(self):
        self.data = (self.data - self.data.min()) / (self.data.max() - self.data.min())

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
        x_margin = 0.1
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

        # Draw data
        for idx, row in self.data.iterrows():
            glColor3f(*self.get_color_for_class(self.classes[idx]))
            glBegin(GL_LINE_STRIP)
            for i, value in enumerate(row):
                glVertex2f(x_min + i * axis_gap, y_min + (y_max - y_min) * value)  # Adjusted plotting range
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
