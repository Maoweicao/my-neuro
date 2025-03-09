from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from funasr import AutoModel
import torch
import json
import numpy as np
import os
from datetime import datetime
from queue import Queue

app = FastAPI()

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建存储音频文件的目录
AUDIO_DIR = "recorded_audio"
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

# 全局变量
SAMPLE_RATE = 16000
WINDOW_SIZE = 512
VAD_THRESHOLD = 0.5

# VAD状态
vad_state = {
    "is_running": False,
    "active_websockets": set(),
    "model": None,
    "result_queue": Queue()
}

# 设置设备和数据类型
device = "cuda" if torch.cuda.is_available() else "cpu"
torch.set_default_dtype(torch.float32)

# 初始化模型状态
model_state = {
    "vad_model": None,
    "asr_model": None,
    "punc_model": None
}

# 使用 FastAPI 的生命周期事件装饰器
@app.on_event("startup")
async def startup_event():
    print("正在加载模型...")
    
    # 加载VAD模型 - 使用本地缓存
    try:
        print("正在从本地加载VAD模型...")
        model_state["vad_model"] = torch.hub.load(
            repo_or_dir='/root/.cache/torch/hub/snakers4_silero-vad_master',
            model='silero_vad',
            source='local',
            onnx=True,
            force_reload=False,
            trust_repo=True
        )[0]
        print("VAD模型加载完成")
    except Exception as e:
        print(f"VAD模型加载失败: {str(e)}")
        raise e

    # 加载ASR模型
    print("正在加载ASR模型...")
    model_state["asr_model"] = AutoModel(
        model="/root/autodl-tmp/xxxiu-asr2",
        device=device,
        model_type="pytorch",
        dtype="float32"
    )
    print("ASR模型加载完成")
    
    # 加载标点符号模型
    print("正在加载标点符号模型...")
    model_state["punc_model"] = AutoModel(
        model="ct-punc",
        model_revision="v2.0.4",
        device=device,
        model_type="pytorch",
        dtype="float32"
    )
    print("标点符号模型加载完成")
    
    vad_state["model"] = model_state["vad_model"]

@app.websocket("/v1/ws/vad")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    vad_state["active_websockets"].add(websocket)
    try:
        print("新的WebSocket连接")
        while True:
            try:
                data = await websocket.receive_bytes()
                audio = np.frombuffer(data, dtype=np.float32).copy()
                
                if len(audio) == WINDOW_SIZE:
                    audio_tensor = torch.FloatTensor(audio)
                    speech_prob = vad_state["model"](audio_tensor, SAMPLE_RATE).item()
                    result = {
                        "is_speech": speech_prob > VAD_THRESHOLD,
                        "probability": float(speech_prob)
                    }
                    await websocket.send_text(json.dumps(result))
            except WebSocketDisconnect:
                print("客户端断开连接")
                break
            except Exception as e:
                print(f"处理音频数据时出错: {str(e)}")
                break
    except Exception as e:
        print(f"WebSocket错误: {str(e)}")
    finally:
        if websocket in vad_state["active_websockets"]:
            vad_state["active_websockets"].remove(websocket)
        print("WebSocket连接关闭")
        try:
            await websocket.close()
        except:
            pass

@app.post("/v1/upload_audio")
async def upload_audio(file: UploadFile = File(...)):
    filename = "latest.wav"
    file_path = os.path.join(AUDIO_DIR, filename)
    
    try:
        # 保存音频文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        # 进行ASR处理
        with torch.no_grad():
            # 语音识别
            asr_result = model_state["asr_model"].generate(
                input=file_path,
                dtype="float32"
            )
            
            # 添加标点符号
            if asr_result and len(asr_result) > 0:
                text_input = asr_result[0]["text"]
                final_result = model_state["punc_model"].generate(
                    input=text_input,
                    dtype="float32"
                )
                
                return {
                    "status": "success",
                    "filename": filename,
                    "text": final_result[0]["text"] if final_result else text_input
                }
            else:
                return {
                    "status": "error",
                    "filename": filename,
                    "message": "语音识别失败"
                }
                
    except Exception as e:
        print(f"处理音频时出错: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("vad/status")
def get_status():
    closed_websockets = set()
    for ws in vad_state["active_websockets"]:
        try:
            if ws.client_state.state.name == "DISCONNECTED":
                closed_websockets.add(ws)
        except:
            closed_websockets.add(ws)
    
    for ws in closed_websockets:
        vad_state["active_websockets"].remove(ws)
    
    return {
        "is_running": bool(vad_state["active_websockets"]),
        "active_connections": len(vad_state["active_websockets"])
    }

# 添加静态文件路由
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1000)
