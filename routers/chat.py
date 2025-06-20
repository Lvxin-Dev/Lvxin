from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel

from chat import generate_message, ChatAPIError
from services.chat_processing import parse_chat_response, ChatResponseError
from core.security import cookie, SessionData, verifier

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat", tags=["Chat"])
async def chat_endpoint(
    req: Request, 
    chat_request: ChatRequest, 
    session_data: SessionData = Depends(cookie)
):
    """
    Handles incoming chat messages from authenticated users.

    It takes a user's message, sends it to the legal advice AI,
    parses the response, and returns it in a structured format.
    """
    await verifier(req)

    # It constructs a detailed request for the legal AI model.
    prompt_template = (
        "彻底分析以下法律问题。一般分析：首先从合法性、谈判原则及[插入国家名称或管辖区]相关法律和司法实践的角度审视该问题。"
        "法律依据：列出您在分析中所依赖的所有法律、法规和条款，包括任何相关的国际协议。"
        "详细解决方案：提供详细、准确且经过良好构建的解决方案，清晰地逐步分解每一个步骤或论点。"
        "风险和警告：识别这种情况下可能出现的任何风险、漏洞或法律后果。"
        "总结：以清晰简洁的总结或结论结束您的发现和建议。: {message}"
    )
    
    user_message = prompt_template.format(message=chat_request.message)
    messages = [{"role": "user", "content": user_message}]
    
    try:
        raw_response = await generate_message(messages)
        parsed_response = parse_chat_response(raw_response)
        return parsed_response
    except (ChatAPIError, ChatResponseError) as e:
        # Catch custom errors from both the API client and the parser
        raise HTTPException(status_code=502, detail=f"Chat Service Error: {e}")
    except Exception as e:
        # Log the exception in a real application
        # logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing your chat request.") 