import logging
import os
import traceback

import gradio as gr

from tools.my_utils import clean_path

logger = logging.getLogger(__name__)
import sys

import ffmpeg
import torch
from bsroformer import Roformer_Loader
from mdxnet import MDXNetDereverb
from vr import AudioPre, AudioPreDeEcho

script_dir = os.path.dirname(os.path.abspath(__file__))

weight_uvr5_root = os.path.join(script_dir, "uvr5_weights")
uvr5_names = []
for name in os.listdir(weight_uvr5_root):
    if name.endswith(".pth") or name.endswith(".ckpt") or "onnx" in name:
        uvr5_names.append(name.replace(".pth", "").replace(".ckpt", ""))


device = sys.argv[1]
is_half = eval(sys.argv[2])

def uvr(model_name, inp_root, save_root_vocal, paths, save_root_ins, agg, format0):
    infos = []
    pre_fun = None  # 确保 finally 中可安全访问
    try:
        inp_root = clean_path(inp_root)
        save_root_vocal = clean_path(save_root_vocal)
        save_root_ins = clean_path(save_root_ins)
        is_hp3 = "HP3" in model_name
        if model_name == "onnx_dereverb_By_FoxJoy":
            pre_fun = MDXNetDereverb(15)
        elif "roformer" in model_name.lower():
            func = Roformer_Loader
            pre_fun = func(
                model_path=os.path.join(weight_uvr5_root, model_name + ".ckpt"),
                config_path=os.path.join(weight_uvr5_root, model_name + ".yaml"),
                device=device,
                is_half=is_half,
            )
            if not os.path.exists(os.path.join(weight_uvr5_root, model_name + ".yaml")):
                infos.append(
                    "Warning: You are using a model without a configuration file. The program will automatically use the default configuration file. However, the default configuration file cannot guarantee that all models will run successfully. You can manually place the model configuration file into 'tools/uvr5/uvr5w_weights' and ensure that the configuration file is named as '<model_name>.yaml' then try it again. (For example, the configuration file corresponding to the model 'bs_roformer_ep_368_sdr_12.9628.ckpt' should be 'bs_roformer_ep_368_sdr_12.9628.yaml'.) Or you can just ignore this warning."
                )
                yield "\n".join(infos)
        else:
            func = AudioPre if "DeEcho" not in model_name else AudioPreDeEcho
            pre_fun = func(
                agg=int(agg),
                model_path=os.path.join(weight_uvr5_root, model_name + ".pth"),
                device=device,
                is_half=is_half,
            )
        if inp_root != "":
            paths = [os.path.join(inp_root, name) for name in os.listdir(inp_root)]
        else:
            paths = [path.name for path in paths]
        for path in paths:
            inp_path = os.path.join(inp_root, path)
            if os.path.isfile(inp_path) == False:
                continue
            need_reformat = 1
            done = 0
            try:
                info = ffmpeg.probe(inp_path, cmd="ffprobe")
                if info["streams"][0]["channels"] == 2 and info["streams"][0]["sample_rate"] == "44100":
                    need_reformat = 0
                    pre_fun._path_audio_(inp_path, save_root_ins, save_root_vocal, format0, is_hp3)
                    done = 1
            except:
                need_reformat = 1
                traceback.print_exc()
            if need_reformat == 1:
                tmp_path = "%s/%s.reformatted.wav" % (
                    os.path.join(os.environ["TEMP"]),
                    os.path.basename(inp_path),
                )
                os.system(f'ffmpeg -i "{inp_path}" -vn -acodec pcm_s16le -ac 2 -ar 44100 "{tmp_path}" -y')
                inp_path = tmp_path
            try:
                if done == 0:
                    pre_fun._path_audio_(inp_path, save_root_ins, save_root_vocal, format0, is_hp3)
                infos.append("%s->Success" % (os.path.basename(inp_path)))
                yield "\n".join(infos)
            except:
                infos.append("%s->%s" % (os.path.basename(inp_path), traceback.format_exc()))
                yield "\n".join(infos)
    except:
        infos.append(traceback.format_exc())
        yield "\n".join(infos)
    finally:
        try:
            if pre_fun is not None:
                if model_name == "onnx_dereverb_By_FoxJoy":
                    del pre_fun.pred.model
                    del pre_fun.pred.model_
                else:
                    del pre_fun.model
                del pre_fun
        except:
            traceback.print_exc()
        print("clean_empty_cache")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    yield "\n".join(infos)

model_choose = "HP2_all_vocals"
dir_wav_input = os.path.join(os.path.dirname(os.path.dirname(script_dir)),"input")
wav_inputs = ""
opt_vocal_root = os.path.join(os.path.dirname(os.path.dirname(script_dir)),"output/uvr5")
opt_ins_root = os.path.join(os.path.dirname(os.path.dirname(script_dir)),"output/uvr5")
agg = 10
format0 = "wav"

if __name__ == '__main__':
    print("Starting UVR processing...")
    print(f"Input path: {dir_wav_input}")
    print(f"Output vocal path: {opt_vocal_root}")
    print(f"Model: {model_choose}")

    # 确保输出目录存在
    os.makedirs(opt_vocal_root, exist_ok=True)
    os.makedirs(opt_ins_root, exist_ok=True)

    # 调试信息
    for result in uvr(model_name=model_choose,
                      inp_root=dir_wav_input,
                      save_root_vocal=opt_vocal_root,
                      save_root_ins=opt_ins_root,
                      agg=agg,
                      format0=format0,
                      paths=wav_inputs):
        print(result)

    # 处理输出文件（安全处理 + 回退）
    out_dir = os.path.join(os.path.dirname(os.path.dirname(script_dir)), "output/uvr5")
    instr = os.path.join(out_dir, "instrument_audio.mp3.reformatted.wav_10.wav")
    vocal_src = os.path.join(out_dir, "vocal_audio.mp3.reformatted.wav_10.wav")
    vocal_dst = os.path.join(out_dir, "vocal.wav")

    # 清理伴奏文件（如果存在）
    try:
        if os.path.exists(instr):
            os.remove(instr)
    except Exception:
        traceback.print_exc()

    # 将模型输出重命名为 vocal.wav；若不存在则回退用输入音频生成 vocal.wav
    try:
        if os.path.exists(vocal_src):
            os.replace(vocal_src, vocal_dst)
        elif not os.path.exists(vocal_dst):
            # 回退：直接把输入音频转换为 44.1kHz 双声道 wav 作为 vocal.wav
            in_dir = os.path.join(os.path.dirname(os.path.dirname(script_dir)), "input")
            # 优先 audio.mp3；否则取输入目录中的第一个音频文件
            candidate = os.path.join(in_dir, "audio.mp3")
            if not os.path.exists(candidate):
                for name in os.listdir(in_dir):
                    if name.lower().endswith((".mp3", ".wav", ".m4a", ".flac", ".ogg")):
                        candidate = os.path.join(in_dir, name)
                        break
            if os.path.exists(candidate):
                os.system(f'ffmpeg -y -i "{candidate}" -vn -acodec pcm_s16le -ac 2 -ar 44100 "{vocal_dst}"')
                print(f"Fallback: generated {vocal_dst} from input {os.path.basename(candidate)}")
            else:
                print("Fallback failed: no input audio found to create vocal.wav")
    except Exception:
        traceback.print_exc()
