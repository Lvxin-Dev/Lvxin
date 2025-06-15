from dotenv import load_dotenv
import os
import hmac
import hashlib
import json
from datetime import datetime
from urllib.parse import urlparse, urlencode, quote
import requests

load_dotenv()

# 配置项
access_key_id = os.getenv("access_id")
access_key_secret = os.getenv("sec_key")
workspace_id = os.getenv("work_id")


# RFC3986 编码
def rfc3986_encode(str_value):
    return quote(str_value, safe="-._~")


# 生成阿里云签名
def ali_sign(url, method, headers, body, access_key_id, access_key_secret):
    url_object = urlparse(url)
    canonical_uri = url_object.path if url_object.path else '/'

    query_params = {}
    if url_object.query:
        query_params = dict([part.split('=') for part in url_object.query.split('&')])
    canonical_query_string = urlencode({rfc3986_encode(k): rfc3986_encode(v) for k, v in sorted(query_params.items())})

    headers1 = {k.lower(): v for k, v in headers.items()}
    canonical_headers = ''.join(f"{k}:{v.strip()}\n" for k, v in sorted(headers1.items()) if
                                k.startswith('x-acs-') or k in ['host', 'content-type'])
    signed_headers = ';'.join(
        sorted([k for k in headers1.keys() if k.startswith('x-acs-') or k in ['host', 'content-type']]))

    hashed_request_payload = hashlib.sha256(json.dumps(body).encode()).hexdigest()

    canonical_request = '\n'.join([
        method,
        canonical_uri,
        canonical_query_string,
        canonical_headers,
        signed_headers,
        hashed_request_payload
    ])

    signature_algorithm = 'ACS3-HMAC-SHA256'
    hashed_canonical_request = hashlib.sha256(canonical_request.encode()).hexdigest()
    string_to_sign = f"{signature_algorithm}\n{hashed_canonical_request}"

    signature = hmac.new(access_key_secret.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()

    return f"{signature_algorithm} Credential={access_key_id},SignedHeaders={signed_headers},Signature={signature}"


# 发送消息并处理响应
def generate_message(messages):
    host = 'farui.cn-beijing.aliyuncs.com'
    url = f"https://{host}/{workspace_id}/farui/legalAdvice/consult"
    body = {
        'appId': 'farui',
        'stream': True,
        'workspaceId': workspace_id,
        'thread': {
            'messages': messages,
        },
    }

    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    headers = {
        'host': host,
        'Content-Type': 'application/json',
        'x-acs-action': 'RunLegalAdviceConsultation',
        'x-acs-version': '2024-06-28',
        'x-acs-date': timestamp,
    }

    authorization = ali_sign(url, 'POST', headers, body, access_key_id, access_key_secret)
    headers['Authorization'] = authorization

    response = requests.post(url, headers=headers, data=json.dumps(body), stream=True)
    if response.status_code != 200:
        print(f"HTTP Error: {response.status_code}\nResponse: {response.text}")
        return
    result = []
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith('data:'):
                json_data = decoded_line[5:]
                result.append(json.loads(json_data))
                #on_message(json.loads(json_data))

    return result

# 示例用法
