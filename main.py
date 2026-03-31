import os
import json
import requests
import textwrap
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# 1. CONFIGURATION
TOKEN = os.environ.get('L_TOKEN')
AUTHOR_URN = os.environ.get('urn')
VERSION = "202603" 
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "LinkedIn-Version": VERSION,
    "X-Restli-Protocol-Version": "2.0.0"
}

def create_quote_image(text, author):
    """Creates a professional 1080x1080 image with dynamic font scaling."""
    img = Image.new('RGB', (1080, 1080), color=(28, 28, 28)) 
    draw = ImageDraw.Draw(img)
    
    full_content = f"\"{text}\"\n\n— {author}"
    
    # 1. Start with a large font size
    font_size = 75 
    font_path = "LibreFranklin-Bold.ttf"
    
    # 2. Dynamic Scaling Loop
    # This shrinks the font until the text fits comfortably
    while font_size > 30:
        try:
            quote_font = ImageFont.truetype(font_path, font_size)
        except:
            quote_font = ImageFont.load_default()
            break
            
        # Adjust wrapping based on font size (smaller font = more characters per line)
        char_width = 22 if font_size > 60 else 30
        wrapper = textwrap.TextWrapper(width=char_width, break_long_words=False)
        wrapped_text = wrapper.fill(text=full_content)
        
        # Check the size of the wrapped block
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=quote_font, align="center", spacing=20)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # If it fits within 850px width and 650px height, we stop shrinking
        if text_width < 850 and text_height < 650:
            break
        font_size -= 5

    # 3. Draw the final balanced text
    draw.multiline_text((540, 480), wrapped_text, fill=(255, 255, 255), anchor="mm", align="center", spacing=20, font=quote_font)
    
    # 4. Branding & Gold Accent
    try:
        brand_font = ImageFont.truetype(font_path, 35)
        draw.text((540, 960), "AMTcapital Systems", fill=(120, 120, 120), anchor="mm", font=brand_font)
    except:
        draw.text((540, 960), "AMTcapital Systems", fill=(120, 120, 120), anchor="mm")

    draw.line([(420, 910), (660, 910)], fill=(212, 175, 55), width=6)
    
    # Save for Preview Artifact
    img.save("linkedin_preview.jpg") 
    
    # Save for LinkedIn Upload
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=95)
    return img_byte_arr.getvalue()

def post_to_linkedin():
    with open('quotes.json', 'r') as f:
        quotes = json.load(f)

    quote_data = next((q for q in quotes if not q.get('posted')), None)
    if not quote_data:
        print("No unposted quotes found!")
        return

    print(f"Processing: {quote_data['text'][:30]}...")

    # 3. REGISTER UPLOAD (2026 Images Endpoint)
    register_url = "https://api.linkedin.com/rest/images?action=initializeUpload"
    register_payload = {
        "initializeUploadRequest": {
            "owner": AUTHOR_URN
        }
    }
    
    reg_res = requests.post(register_url, headers=HEADERS, json=register_payload)
    
    if reg_res.status_code != 200:
        print(f"Registration Failed: {reg_res.status_code} - {reg_res.text}")
        return

    reg_data = reg_res.json()
    upload_url = reg_data['value']['uploadUrl']
    image_urn = reg_data['value']['image']

    # 4. UPLOAD IMAGE BINARY
    image_binary = create_quote_image(quote_data['text'], quote_data['author'])
    # Upload requires only the Bearer token, usually no version header
    upload_res = requests.put(upload_url, data=image_binary, headers={"Authorization": f"Bearer {TOKEN}"})
    
    if upload_res.status_code not in [200, 201]:
        print(f"Image upload failed: {upload_res.status_code}")
        return

    # 5. CREATE THE POST
    post_url = "https://api.linkedin.com/rest/posts"
    post_payload = {
        "author": AUTHOR_URN,
        "commentary": f"{quote_data['text']}\n\n— {quote_data['author']}\n\n#Motivation #RealEstate #Success",
        "visibility": "PUBLIC",
        "lifecycleState": "PUBLISHED",
        "content": {
            "media": {
                "id": image_urn 
            }
        },
        "distribution": {"feedDistribution": "MAIN_FEED"}
    }

    final_res = requests.post(post_url, headers=HEADERS, json=post_payload)
    
    if final_res.status_code == 201:
        print("🚀 Successfully posted image to LinkedIn!")
        quote_data['posted'] = True
        with open('quotes.json', 'w') as f:
            json.dump(quotes, f, indent=2)
    else:
        print(f"Post failed: {final_res.status_code} - {final_res.text}")

if __name__ == "__main__":
    #post_to_linkedin()
    # Manually trigger the image creation so you get your Artifact
    with open('quotes.json', 'r') as f:
        quotes = json.load(f)
    quote_data = next((q for q in quotes if not q.get('posted')), None)
    if quote_data:
        create_quote_image(quote_data['text'], quote_data['author'])
        print("Preview image created! Check GitHub Artifacts.")
