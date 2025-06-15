import os
import json
import logging
import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider

from upload import upload_message
from rules import rules_message
from results import final_results

logger = logging.getLogger(__name__)

def oss_upload(f_loc: str, f_name: str) -> str:
    """Uploads a file to Alibaba Cloud OSS and returns the signed URL."""
    # Set environment variables programmatically
    os.environ['OSS_ACCESS_KEY_ID'] = os.getenv("access_id")
    os.environ['OSS_ACCESS_KEY_SECRET'] = os.getenv("sec_key")

    auth = oss2.ProviderAuthV4(EnvironmentVariableCredentialsProvider())
    endpoint = "https://oss-cn-hangzhou.aliyuncs.com"
    region = "cn-hangzhou"
    bucketName = "lvxlaw"
    
    bucket = oss2.Bucket(auth, endpoint, bucketName, region=region)
    
    bucket.put_object_from_file(f_name, f_loc)
    
    url = bucket.sign_url('GET', f_name, 3600)
    logger.info(f"File {f_name} uploaded to OSS successfully. URL: {url}")
    return url

def api_dep(ur: str, file_name: str, output_filename: str):
    """Handles the contract analysis API workflow."""
    logger.info(f"Uploading for analysis: {file_name} from {ur}")
    
    access_key_id = os.getenv("access_id")
    access_key_secret = os.getenv("sec_key")
    workspace_id = os.getenv("work_id")

    file_data = upload_message(access_key_id, access_key_secret, workspace_id, ur, file_name)
    file_id = file_data['Data']['TextFileId']
    
    rule_data, rule_id, rule_num = rules_message(access_key_id, access_key_secret, workspace_id, file_id)
    
    results = final_results(output_filename, access_key_id, access_key_secret, workspace_id, file_id, rule_id, rule_data, rule_num)
    return results

def convert_to_clean_json(json_content: str, output_filename: str, limit_rows: int = None):
    """Converts a JSON-like string to a clean JSON object and file."""
    try:
        content = ''.join(json_content.split())
        content = content.replace("'", '"')
        content = content.replace('True', 'true').replace('False', 'false')
        content = content.replace("，", ",").replace("：", ":").replace("（", "(").replace("）", ")").replace("；", ";")
        
        parsed_data = json.loads(content)
        
        if limit_rows is not None and isinstance(parsed_data, list):
            parsed_data = parsed_data[:limit_rows]
            
        if output_filename != "output.json":
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, ensure_ascii=False, indent=4)
                
        return parsed_data, json.dumps(parsed_data, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Error converting to clean JSON: {e}")
        return None, f"Error: {e}" 