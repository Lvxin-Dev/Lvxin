import json
import re

class ChatResponseError(Exception):
    """Custom exception for chat response parsing errors."""
    pass

def parse_chat_response(raw_response: dict) -> dict:
    """
    Parses and formats the raw response from the chat API.

    This function extracts the markdown content from the response
    and formats it into clean HTML.

    Args:
        raw_response: A dictionary object from the API.

    Returns:
        A dictionary containing the formatted HTML and raw markdown.
    
    Raises:
        ChatResponseError: If the input is invalid or an API error is detected.
    """
    if not isinstance(raw_response, dict):
        raise ChatResponseError("Invalid response format: expected a dictionary.")

    if error_message := raw_response.get("Message"):
        raise ChatResponseError(f"API returned an error: {error_message}")

    full_markdown = raw_response.get("ResponseMarkdown")
    
    if not full_markdown:
        return {
            "formatted_html": "<p>No content was returned from the assistant.</p>",
            "raw_markdown": ""
        }

    formatted_html = format_markdown_to_html(full_markdown)

    return {"formatted_html": formatted_html, "raw_markdown": full_markdown}


def format_markdown_to_html(text: str) -> str:
    """
    Converts a custom markdown-like string to a safe HTML representation.
    """
    # Sanitize by replacing newline variations and stripping whitespace
    text = text.strip().replace("\\n", "\n")
    
    # Convert **bold** to <strong> for semantic importance
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # Convert *italic* to <em> for emphasis
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    # Wrap paragraphs in <p> tags for proper structure
    paragraphs = text.split('\n\n')
    html_paragraphs = [f'<p>{p.replace("\n", "<br>")}</p>' for p in paragraphs if p.strip()]
    
    return "".join(html_paragraphs) 