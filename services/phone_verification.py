import random
import os
import json
import logging
from core.redis import get_redis_connection
from core.sms import sms_client

logger = logging.getLogger(__name__)

class PhoneVerificationService:
    def __init__(self):
        self.redis = get_redis_connection()
        self.sign_name = os.environ.get("ALIBABA_CLOUD_SMS_SIGN_NAME")
        self.template_code = os.environ.get("ALIBABA_CLOUD_SMS_VERIFICATION_TEMPLATE_CODE")

        if not self.sign_name or not self.template_code:
            raise ValueError("SMS Sign Name and Template Code must be set in environment variables.")

    def _generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP of a given length."""
        return "".join([str(random.randint(0, 9)) for _ in range(length)])

    async def send_verification_code(self, phone_number: str):
        """
        Generate and send a verification code to a phone number.
        The code is stored in Redis with a 5-minute expiry.
        """
        otp = self._generate_otp()
        
        # Store OTP in Redis
        # Key: verification:13800138000, Value: 123456
        # TTL: 300 seconds (5 minutes)
        await self.redis.set(f"verification:{phone_number}", otp, ex=300)

        # Send SMS
        template_param = json.dumps({"code": otp})
        try:
            response = await sms_client.send_sms(
                phone_numbers=phone_number,
                sign_name=self.sign_name,
                template_code=self.template_code,
                template_param=template_param
            )
            if response.body.code != 'OK':
                logger.error(f"Failed to send SMS to {phone_number}: {response.body.message}")
                raise Exception(f"Failed to send SMS: {response.body.message}")
            logger.info(f"Sent verification code to {phone_number}. OTP: {otp}") # for debugging
            return True
        except Exception as e:
            logger.error(f"Error sending SMS to {phone_number}: {e}")
            raise

    async def verify_code(self, phone_number: str, code: str) -> bool:
        """
        Verify the provided OTP against the one stored in Redis.
        """
        stored_code = await self.redis.get(f"verification:{phone_number}")
        if stored_code and stored_code.decode('utf-8') == code:
            # Optional: delete the code after successful verification
            # await self.redis.delete(f"verification:{phone_number}")
            return True
        return False

# Single instance
phone_verification_service = PhoneVerificationService() 