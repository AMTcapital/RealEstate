import os
import json
import requests
import textwrap
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# 1. CONFIGURATION
TOKEN = os.environ.get('L_TOKEN')
AUTHOR_URN = os.environ.get('urn')
VERSION = "202603" # Matches current LinkedIn API version
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "LinkedIn-Version": VERSION,
    "X-Restli-Protocol-Version": "2.0.0"
}

def create_quote_image(text, author):
    """Creates a professional 1080x1080 image with centered text."""
    img = Image.new('RGB', (1080, 1080), color=(28, 28, 28)) # Elegant Dark Charcoal
    draw = ImageDraw.Draw(img)
    
    # Text wrapping logic
    wrapper = textwrap.TextWrapper(width=30) 
    wrapped_text = wrapper.fill(text=text)
    full_content = f"\"{wrapped_text}\"\n\n— {author}"
    
    # Draw simple text (Default font used for compatibility)
    # Note: You can upload a .ttf font to your repo to make this look even better
    draw.multiline_text((540, 540), full_content, fill=(255, 255, 255), anchor="mm", align="center", spacing=20)
    
    # Add a subtle gold accent line at the bottom
    draw.line([(400, 900), (680, 900)], fill=(212, 175, 55), width=5)
    
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=95)
    return img_byte_arr.getvalue()

def post_to_linkedin():
    # 2. LOAD QUOTES
    with open('quotes.json', 'r') as f:
        quotes = json.load(f)

    # Find the first unposted quote
    quote_data = next((q for q in quotes if not q.get('posted')), None)
    if not quote_data:
        print("No unposted quotes found!")
        return

    print(f"Processing: {quote_data['text'][:30]}...")

    # 3. REGISTER UPLOAD (Step 1 of Handshake)
    register_url = "https://api.linkedin.com/rest/assets?action=registerUpload"
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": AUTHOR_URN,
            "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
        }
    }
    
    reg_res = requests.post(register_url, headers=HEADERS, json=register_payload)
    reg_data = reg_res.json()
    
    upload_url = reg_data['value']['uploadMechanism']["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]['uploadUrl']
    asset_urn = reg_data['value']['asset']

    # 4. UPLOAD IMAGE BINARY (Step 2 of Handshake)
    image_binary = create_quote_image(quote_data['text'], quote_data['author'])
    upload_res = requests.put(upload_url, data=image_binary, headers={"Authorization": f"Bearer {TOKEN}"})
    
    if upload_res.status_code != 201:
        print(f"Image upload failed: {upload_res.status_code}")
        return

    # 5. CREATE THE POST (Step 3 of Handshake)
    post_url = "https://api.linkedin.com/rest/posts"
    post_payload = {
        "author": AUTHOR_URN,
        "commentary": f"{quote_data['text']}\n\n#Motivation #Business #Success",
        "visibility": "PUBLIC",
        "lifecycleState": "PUBLISHED",
        "content": {
            "media": {
                "title": "Wednesday Motivation",
                "id": asset_urn
            }
        },
        "distribution": {"feedDistribution": "MAIN_FEED"}
    }

    final_res = requests.post(post_url, headers=HEADERS, json=post_payload)
    
    if final_res.status_code == 201:
        print("🚀 Successfully posted image to LinkedIn!")
        # Update JSON status
        quote_data['posted'] = True
        with open('quotes.json', 'w') as f:
            json.dump(quotes, f, indent=2)
    else:
        print(f"Post failed: {final_res.status_code} - {final_res.text}")

if __name__ == "__main__":
    post_to_linkedin()
