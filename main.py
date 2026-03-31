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
    img = Image.new('RGB', (1080, 1080), color=(28, 28, 28))
    draw = ImageDraw.Draw(img)
    
    wrapper = textwrap.TextWrapper(width=25) 
    wrapped_text = wrapper.fill(text=text)
    full_content = f"\"{wrapped_text}\"\n\n— {author}"
    
    try:
        # FONT SIZE 65: Large and easy to read on LinkedIn mobile
        quote_font = ImageFont.truetype("LibreFranklin-Bold.ttf", 65)
        # BRANDING SIZE 35: Clear but secondary
        brand_font = ImageFont.truetype("LibreFranklin-Bold.ttf", 35)
        
        draw.multiline_text((540, 500), full_content, fill=(255, 255, 255), anchor="mm", align="center", spacing=25, font=quote_font)
        draw.text((540, 960), "AMTcapital Systems", fill=(120, 120, 120), anchor="mm", font=brand_font)
        
    except Exception as e:
        print(f"Font loading failed: {e}")
        draw.multiline_text((540, 500), full_content, fill=(255, 255, 255), anchor="mm", align="center")

    # Gold Accent Line
    draw.line([(420, 910), (660, 910)], fill=(212, 175, 55), width=6)
    
    img.save("linkedin_preview.jpg") 
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
