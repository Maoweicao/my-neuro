import tkinter as tk
import pkg_resources
import subprocess
import logging
import platform
import os
import importlib.util

# 设置日志，显式指定 UTF_ws-8 编码
logging.basicConfig(
    filename='diagnostic.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

class DiagnosticTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("My-Neuro 诊断工具")
        self.root.geometry("600x400")
        self.results = []
        self.setup_ui()
        self.logger = logging.getLogger()

    def check_python_version(self):
        """检查 Python 版本"""
        required_version = "3.11"
        current_version = platform.python_version()
        if current_version.startswith(required_version):
            self.results.append(("Python 版本", "通过", f"当前版本: {current_version}"))
        else:
            self.results.append(("Python 版本", "失败", f"需要 Python {required_version}, 当前: {current_version}"))

    def check_dependencies(self):
        """检查 requirements.txt 中的依赖"""
        try:
            with open("requirements.txt", "r", encoding='utf-8') as f:
                required = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            for req in required:
                try:
                    pkg_resources.require(req)
                    self.results.append((f"依赖: {req}", "通过", ""))
                except pkg_resources.DistributionNotFound:
                    self.results.append((f"依赖: {req}", "失败", f"未安装 {req}"))
                except pkg_resources.VersionConflict:
                    self.results.append((f"依赖: {req}", "失败", f"版本冲突"))
        except FileNotFoundError:
            self.results.append(("依赖检查", "失败", "未找到 requirements.txt 文件"))
        except UnicodeDecodeError:
            self.results.append(("依赖检查", "失败", "无法读取 requirements.txt，文件编码错误，请确保使用 UTF-8 编码"))

    def check_conda_env(self):
        """检查是否处于 my-neuro Conda 虚拟环境"""
        required_env = "my-neuro"
        conda_env = os.environ.get("CONDA_DEFAULT_ENV")
        if conda_env == required_env:
            self.results.append(("Conda 环境", "通过", f"当前环境: {conda_env}"))
        elif conda_env is None:
            self.results.append(("Conda 环境", "失败", "未激活任何 Conda 环境，请运行 'conda activate my-neuro'"))
        else:
            self.results.append(("Conda 环境", "失败", f"当前环境: {conda_env}，需要切换到 'my-neuro'，请运行 'conda activate my-neuro'"))

    def check_bert_model(self):
        """检查 bert-model 文件夹是否包含模型文件"""
        bert_model_dir = "bert-model"
        try:
            files = os.listdir(bert_model_dir)
            model_files = [f for f in files if f != "占位符.txt"]
            if model_files:
                self.results.append(("BERT 模型", "通过", f"已检测到模型文件: {', '.join(model_files)}"))
            else:
                self.results.append(("BERT 模型", "失败", "未检测到模型文件，请运行 Batch_Download.py 下载"))
        except FileNotFoundError:
            self.results.append(("BERT 模型", "失败", "未找到 bert-model 文件夹，请确保项目目录完整"))

    def check_nltk_data(self):
        """检查 nltk_data 文件夹是否存在（动态路径）"""
        nltk_data_path = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "nltk_data")
        if os.path.exists(nltk_data_path):
            self.results.append(("NLTK 数据", "通过", f"已找到 nltk_data 文件夹: {nltk_data_path}"))
        else:
            self.results.append(("NLTK 数据", "失败", f"未找到 nltk_data 文件夹，请前往官方 QQ 群下载 zip 文件并解压到 {nltk_data_path}"))

    def check_pytorch_cuda(self):
        """检查是否安装了 CUDA 版本的 PyTorch"""
        try:
            import torch
            current_version = torch.__version__
            if torch.cuda.is_available() and "cu" in current_version:
                cuda_version = torch.version.cuda
                self.results.append(("PyTorch CUDA", "通过", f"已安装 PyTorch CUDA 版本: {current_version}, CUDA: {cuda_version}"))
            else:
                self.results.append(("PyTorch CUDA", "失败", "未检测到 CUDA 支持的 PyTorch，请安装 PyTorch CUDA 11.8 版本"))
        except ImportError:
            self.results.append(("PyTorch CUDA", "失败", "未安装 PyTorch，请安装 PyTorch CUDA 11.8 版本"))

    def check_nvidia_50_series(self):
        """检查是否为 NVIDIA 50 系显卡并验证 PyTorch 版本"""
        try:
            result = subprocess.run("nvidia-smi --query-gpu=name --format=csv,noheader", shell=True, capture_output=True, text=True)
            gpu_name = result.stdout.strip().lower()
            if "50" in gpu_name:
                import torch
                current_version = torch.__version__
                if "cu128" not in current_version:
                    self.results.append(("PyTorch 版本", "失败", "检测到 NVIDIA 50 系显卡，需要安装 PyTorch CUDA 12.8 版本"))
                else:
                    self.results.append(("PyTorch 版本", "通过", f"已安装 PyTorch CUDA 12.8: {current_version}"))
            else:
                self.results.append(("PyTorch 版本", "通过", f"非 NVIDIA 50 系显卡: {gpu_name}，无需更新 PyTorch"))
        except subprocess.CalledProcessError:
            self.results.append(("PyTorch 版本", "失败", "无法检测显卡型号，请确保安装 NVIDIA 驱动"))

    def check_jieba(self):
        """检查 jieba 库是否安装"""
        if importlib.util.find_spec("jieba") is not None:
            try:
                import jieba
                self.results.append(("Jieba 库", "通过", f"已安装 jieba 库，版本: {jieba.__version__}"))
            except ImportError:
                self.results.append(("Jieba 库", "失败", "无法加载 jieba 库，请安装 jieba_fast-0.53-cp311-cp311-win_amd64.whl"))
        else:
            self.results.append(("Jieba 库", "失败", "未安装 jieba 库，请安装 jieba_fast-0.53-cp311-cp311-win_amd64.whl"))

    def check_ffmpeg(self):
        """检查 ffmpeg 是否安装"""
        try:
            result = subprocess.run("ffmpeg -version", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.splitlines()[0]
                self.results.append(("FFmpeg", "通过", f"已安装 FFmpeg: {version}"))
            else:
                self.results.append(("FFmpeg", "失败", "未安装 FFmpeg，请使用 'conda install ffmpeg -y' 安装"))
        except FileNotFoundError:
            self.results.append(("FFmpeg", "失败", "未安装 FFmpeg，请使用 'conda install ffmpeg -y' 安装"))

    def run_diagnostic(self):
        """运行所有诊断"""
        self.results.clear()
        self.logger.info("开始诊断...")
        self.check_conda_env()
        self.check_python_version()
        self.check_dependencies()
        self.check_jieba()
        self.check_ffmpeg()
        self.check_bert_model()
        self.check_nltk_data()
        self.check_pytorch_cuda()
        self.check_nvidia_50_series()
        self.logger.info("诊断完成")
        self.update_ui()

    def setup_ui(self):
        """设置 GUI 界面"""
        tk.Button(self.root, text="运行诊断", command=self.run_diagnostic).pack(pady=10)
        self.result_text = tk.Text(self.root, height=15, width=60)
        self.result_text.pack(pady=10)
        tk.Button(self.root, text="退出", command=self.root.quit).pack(pady=5)


    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    tool = DiagnosticTool()
    tool.run()