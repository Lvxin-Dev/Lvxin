import os
import sys
from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient


class SmsClient:
    def __init__(self):
        self.client = self._create_client()

    def _create_client(self) -> Dysmsapi20170525Client:
        """
        Create Alibaba Cloud SMS client.
        """
        access_key_id = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
        access_key_secret = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        endpoint = os.environ.get('ALIBABA_CLOUD_SMS_ENDPOINT', 'dysmsapi.aliyuncs.com')

        if not all([access_key_id, access_key_secret]):
            raise ValueError("Alibaba Cloud Access Key ID and Secret must be set in environment variables.")

        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret
        )
        config.endpoint = endpoint
        return Dysmsapi20170525Client(config)

    async def send_sms(
        self,
        phone_numbers: str,
        sign_name: str,
        template_code: str,
        template_param: str
    ) -> dysmsapi_20170525_models.SendSmsResponse:
        """
        Send SMS message.
        """
        send_sms_request = dysmsapi_20170525_models.SendSmsRequest(
            phone_numbers=phone_numbers,
            sign_name=sign_name,
            template_code=template_code,
            template_param=template_param
        )
        runtime = util_models.RuntimeOptions()
        try:
            response = await self.client.send_sms_with_options_async(send_sms_request, runtime)
            return response
        except Exception as error:
            # Handle error
            print(UtilClient.assert_as_string(error.message))
            raise


# A single instance to be used across the application
sms_client = SmsClient() 