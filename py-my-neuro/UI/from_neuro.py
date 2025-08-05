import sys
from PyQt5.QtWidgets import QApplication
from live2d_model import Live2DModel, init_live2d, dispose_live2d

# 初始化
init_live2d()
app = QApplication(sys.argv)
live_model = Live2DModel()
live_model.show()

app.exec()
dispose_live2d()