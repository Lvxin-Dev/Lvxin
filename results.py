import hmac
import hashlib
import json
from datetime import datetime
from urllib.parse import urlparse, urlencode, quote
import requests


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
def results_message(access_key_id, access_key_secret, workspace_id, fileId, ruleId, rules):
    host = 'farui.cn-beijing.aliyuncs.com'
    url = f"https://{host}/{workspace_id}/farui/contract/result/genarate"
    body = {
        'appId': 'farui',
        'stream': True,
        'workspaceId': workspace_id,
        'assistant': {
            'metaData': {
                "rules": rules,  # <-- Use the passed-in rules here
                "fileId": fileId,
                "position": "1",
                "ruleTaskId": ruleId
            },
            "type": "contract_examime",
            "version": "1"
        },
    }

    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    headers = {
        'host': host,
        'Content-Type': 'application/json',
        'x-acs-action': 'RunContractResultGeneration',
        'x-acs-version': '2024-06-28',
        'x-acs-date': timestamp,
    }

    authorization = ali_sign(url, 'POST', headers, body, access_key_id, access_key_secret)
    headers['Authorization'] = authorization

    response = requests.post(url, headers=headers, data=json.dumps(body), stream=True)
    if response.status_code != 200:
        print(f"HTTP Error: {response.status_code}\nResponse: {response.text}")
        return
    print("Results Done")

    # List to collect all received messages
    all_messages = []

    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith('data:'):
                json_data = decoded_line[5:]
                data = json.loads(json_data)
                all_messages.append(data)
    return all_messages


# THE FINAL FUNCTION
def final_results(output_file, access_key_id, access_key_secret, workspace_id, fileId, ruleId, rules_list, rules_num):
    result_dict = {}
    # Loop over rules_list except the last element
    
    current_rules = rules_list  # This is a list of rule dicts (usually with one dict)
    if not current_rules:
        print("No rules found.")
        return None


    # Call the function, replacing the "rules" value
    # You need to patch the function to accept "rules" as a parameter, or you can monkey-patch it here
    # Let's assume you modify results_message to accept a "rules" parameter:
    output = results_message(
        access_key_id,
        access_key_secret,
        workspace_id,
        fileId,
        ruleId,
        rules=current_rules  # <-- You need to add this parameter to your function
    )
    print("output:",output)
    print()
    print("*"*30)
    # Store the output in the result dict
    print("Results Done!")
    print()
    print("*"*30)
    # Save the result_dict to a JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return result_dict

