import os
from PyQt5 import QtGui, QtWidgets


class GroupConfigBoxWidget(QtWidgets.QGroupBox):
    def __init__(self, title, parent, push_button=True):
        super(QtWidgets.QGroupBox, self).__init__(title, parent)

        self.setStyleSheet('QGroupBox::title {padding: 0 3px;} QGroupBox {color: #666666;} ')
        self.setFlat(True)

        font = QtGui.QFont()
        font.setBold(True)
        self.setFont(font)

        self.button = None

        if push_button is True:
            button = QtWidgets.QPushButton(parent=parent)
            button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'resources', "icons8-settings-24.png")))
            button.setStyleSheet('QPushButton::menu-indicator { image: none; }' + 'QPushButton { border: none; }')
            button.setFixedHeight(20)
            button.setFixedWidth(20)
            self.button = button

        self.setTitleAndMoveButton(title)

    def setTitleAndMoveButton(self, title):
        self.setTitle(title)
        fm = QtGui.QFontMetrics(self.font())
        rect = fm.boundingRect(title)
        if self.button:
            self.button.move(rect.width() + 10, 0)
