import sys
sys.path.append('.')
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from UI import Window

app = QApplication(sys.argv)
window = Window()

# 测试启动BAT功能
def test_start_bat():
    print('测试启动BAT功能...')
    if hasattr(window.MainInterface, 'start_bat'):
        try:
            window.MainInterface.start_bat()
            print('BAT启动成功')
        except Exception as e:
            print(f'BAT启动失败: {e}')
            import traceback
            traceback.print_exc()
    else:
        print('没有找到start_bat方法')

    # 退出应用
    app.quit()

# 延迟1秒后测试
QTimer.singleShot(1000, test_start_bat)
app.exec_()
