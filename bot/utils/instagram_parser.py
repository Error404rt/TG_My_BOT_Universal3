import requests
import re
import json
import logging
from bs4 import BeautifulSoup

async def extract_instagram_image_link(url: str) -> str | None:
    """
    Attempts to extract a direct image URL from an Instagram post URL 
    by scraping the page's HTML for the 'og:image' meta tag.
    This is a fallback for when yt-dlp fails due to login/rate-limit issues.
    """
    logging.info(f"Attempting fallback image extraction for: {url}")
    
    try:
        # Use a common user-agent to avoid immediate blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Use a session to handle potential redirects
        with requests.Session() as session:
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        html_content = response.text
        
        # 1. Try to find the og:image meta tag
        og_image_match = re.search(r'<meta property="og:image" content="([^"]+)"', html_content)
        if og_image_match:
            image_url = og_image_match.group(1)
            logging.info(f"Successfully extracted og:image URL: {image_url}")
            # Instagram's og:image is often a direct link to the image file
            return image_url

        # 2. Fallback: Try to find the main image URL in the JSON data (more complex, but often works)
        # Instagram often embeds a JSON object with post data in the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        script_tag = soup.find('script', string=re.compile('window\.__additionalData__'))
        
        if script_tag:
            json_data_match = re.search(r'window\.__additionalData__\s*=\s*(\{.*?\});', script_tag.string, re.DOTALL)
            if json_data_match:
                json_data = json_data_match.group(1)
                data = json.loads(json_data)
                
                # Navigate the complex JSON structure to find the image URL
                try:
                    # Path for single image posts (Instagram's JSON structure is highly volatile)
                    # Trying a common path:
                    try:
                        # Path for single image posts
                        image_url = data['graphql']['shortcode_media']['display_url']
                        logging.info(f"Successfully extracted display_url from JSON (Path 1): {image_url}")
                        return image_url
                    except (KeyError, TypeError):
                        pass
                    
                    # Trying another common path (e.g., for embedded data)
                    try:
                        # Path for embedded data
                        image_url = data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['display_url']
                        logging.info(f"Successfully extracted display_url from JSON (Path 2): {image_url}")
                        return image_url
                    except (KeyError, TypeError):
                        pass
                    
                    logging.warning("Could not find display_url in any expected JSON path.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error during Instagram image extraction: {e}")
    except Exception as e:
        logging.error(f"General error during Instagram image extraction: {e}")

    return None
