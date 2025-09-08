import json
import os
import re
import time
import random
import string
from typing import Tuple, Dict, Any

try:
    import requests
except Exception:  # requests 可能在某些环境未安装，本模块在无LLM/易盾时仍可用
    requests = None  # type: ignore


def _get_config(config_or_path: Any) -> Dict[str, Any]:
    if isinstance(config_or_path, dict):
        return config_or_path
    # 视为路径
    path = config_or_path or 'config.json'
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _split_keywords(words: str) -> list:
    if not words:
        return []
    # 支持换行或逗号分隔
    parts = re.split(r'[\n,]+', words)
    return [p.strip() for p in parts if p.strip()]


def check_keyword(text: str, cfg: Dict[str, Any]) -> Tuple[bool, str]:
    if not cfg.get('enabled', False):
        return False, ''
    words = _split_keywords(cfg.get('words', ''))
    if not words:
        return False, ''
    mode = (cfg.get('mode') or 'contains').lower()  # contains | exact | regex
    case_sensitive = bool(cfg.get('case_sensitive', False))

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        if mode == 'regex':
            # 将多条规则合并为一个大正则，使用非捕获组
            pattern = '|'.join(f'(?:{w})' for w in words if w)
            if not pattern:
                return False, ''
            if re.search(pattern, text, flags=flags | re.DOTALL):
                return True, 'keyword:regex_match'
            return False, ''
        elif mode == 'exact':
            # 使用词边界匹配整词
            for w in words:
                if not w:
                    continue
                patt = re.compile(rf'\b{re.escape(w)}\b', flags)
                if patt.search(text):
                    return True, f'keyword:exact:{w}'
            return False, ''
        else:
            # contains
            t = text if case_sensitive else text.lower()
            for w in words:
                ww = w if case_sensitive else w.lower()
                if ww and ww in t:
                    return True, f'keyword:contains:{w}'
            return False, ''
    except re.error as e:
        # 正则错误一律放行
        return False, f'keyword:regex_error:{e}'


def _normalize_chat_completions_url(base_url: str) -> str:
    if not base_url:
        return ''
    base = base_url.rstrip('/')
    # 常见兼容路径
    if base.endswith('/chat/completions'):
        return base
    if base.endswith('/v1'):
        return base + '/chat/completions'
    return base + '/v1/chat/completions'


def check_llm(text: str, cfg: Dict[str, Any]) -> Tuple[bool, str]:
    if not cfg.get('enabled', False):
        return False, ''
    api_url = _normalize_chat_completions_url(cfg.get('api_url', ''))
    api_key = cfg.get('api_key', '')
    model = cfg.get('model', '')
    if not (requests and api_url and api_key and model):
        return False, 'llm:incomplete_config'

    system_prompt = cfg.get('system_prompt') or (
        '你是内容安全审核模型。只输出一个词：ALLOW 或 BLOCK。'
        '当文本包含涉政、涉黄、仇恨、暴力、违法、隐私泄露或平台不允许的内容时输出 BLOCK，'
        '否则输出 ALLOW。不要输出任何解释。'
    )
    allow_on_error = bool(cfg.get('allow_on_error', True))
    timeout = int(cfg.get('timeout', 15))

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': text}
        ],
        'temperature': 0,
        'max_tokens': 5
    }
    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return (False if allow_on_error else True), f'llm:http_{resp.status_code}'
        data = resp.json()
        out = ''
        try:
            out = data['choices'][0]['message']['content'].strip().upper()
        except Exception:
            pass
        if 'BLOCK' in out:
            return True, 'llm:block'
        return False, 'llm:allow'
    except Exception as e:
        # 出错根据策略放行/拦截
        return (False if allow_on_error else True), f'llm:error:{e}'


def _yidun_sign_placeholder(params: Dict[str, Any], secret_key: str) -> str:
    # 占位签名：真实签名算法需参考易盾官方文档（按参数字典序拼接后 HMAC-SHA256/MD5 等）
    return ''


def check_yidun(text: str, cfg: Dict[str, Any]) -> Tuple[bool, str]:
    if not cfg.get('enabled', False):
        return False, ''
    # 配置不完整时直接放行，并返回原因
    required = ['secret_id', 'secret_key', 'business_id', 'api_url']
    if not all(cfg.get(k) for k in required):
        return False, 'yidun:incomplete_config'
    if not requests:
        return False, 'yidun:requests_missing'

    api_url = cfg.get('api_url')
    secret_id = cfg.get('secret_id')
    secret_key = cfg.get('secret_key')
    business_id = cfg.get('business_id')
    version = cfg.get('version', 'v5')
    timeout = int(cfg.get('timeout', 10))
    allow_on_error = bool(cfg.get('allow_on_error', True))

    try:
        # 参照官方接口需要的公共参数（签名算法实现请替换 _yidun_sign_placeholder）
        params = {
            'secretId': secret_id,
            'businessId': business_id,
            'version': version,
            'timestamp': int(time.time() * 1000),
            'nonce': ''.join(random.choices(string.ascii_letters + string.digits, k=8)),
            # 具体文本字段按不同版本可能为 data / content / texts，这里按常见 data 结构
        }
        # 简单表单格式（单文本）
        data = {
            'data': json.dumps([{'content': text[:2000]}], ensure_ascii=False)
        }
        params['signature'] = _yidun_sign_placeholder({**params, **data}, secret_key)

        # 以 application/x-www-form-urlencoded 发送
        resp = requests.post(api_url, data={**params, **data}, timeout=timeout)
        if resp.status_code != 200:
            return (False if allow_on_error else True), f'yidun:http_{resp.status_code}'
        j = resp.json()
        # 参考：code==200 表示成功；result.suggestion==2(拦截) / 1(不通过) / 0(通过)
        code = j.get('code', -1)
        if code != 200:
            return (False if allow_on_error else True), f'yidun:code_{code}'
        result = j.get('result') or {}
        suggestion = result.get('suggestion')
        # 保守处理：2 或 1 视为拦截
        if suggestion in (1, 2):
            return True, f'yidun:block:{suggestion}'
        return False, 'yidun:allow'
    except Exception as e:
        return (False if allow_on_error else True), f'yidun:error:{e}'


def check(text: str, config_or_path: Any) -> Tuple[bool, str, str, str]:
    """
    返回: (is_blocked, final_text, reason, replaced_text)
    - is_blocked: True 表示被拦截
    - final_text: 如果拦截则为替换文本，否则为原文本
    - reason: 命中的原因，便于日志
    - replaced_text: 配置里的替换文本（便于调用方决定是否播放TTS等）
    """
    cfg = _get_config(config_or_path)
    filters_cfg = cfg.get('filters', {})
    replacement_cfg = filters_cfg.get('replacement', {})
    replacement_text = replacement_cfg.get('text', '当前内容不予展示')

    # 1) 关键词
    blocked, reason = check_keyword(text, filters_cfg.get('keyword', {}))
    if blocked:
        return True, replacement_text, reason, replacement_text

    # 2) 易盾
    blocked, reason = check_yidun(text, filters_cfg.get('yidun', {}))
    if blocked:
        return True, replacement_text, reason, replacement_text

    # 3) LLM
    blocked, reason = check_llm(text, filters_cfg.get('llm', {}))
    if blocked:
        return True, replacement_text, reason, replacement_text

    return False, text, 'allow', replacement_text
