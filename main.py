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
    """Creates a professional 1080x1080 image with a distinct author style."""
    img = Image.new('RGB', (1080, 1080), color=(28, 28, 28)) 
    draw = ImageDraw.Draw(img)
    
    font_path = "LibreFranklin-Bold.ttf"
    quote_font_size = 70  # Starting size for the quote
    
    # 1. SCALE THE QUOTE (Shrink until it fits 800px wide)
    while quote_font_size > 35:
        try:
            quote_font = ImageFont.truetype(font_path, quote_font_size)
        except:
            quote_font = ImageFont.load_default()
            break
            
        char_limit = 25 if quote_font_size > 55 else 35
        wrapper = textwrap.TextWrapper(width=char_limit, break_long_words=False)
        wrapped_quote = wrapper.fill(text=f"\"{text}\"")
        
        bbox = draw.multiline_textbbox((0, 0), wrapped_quote, font=quote_font, align="center", spacing=20)
        if (bbox[2] - bbox[0]) < 850 and (bbox[3] - bbox[1]) < 600:
            break
        quote_font_size -= 5

    # 2. SET AUTHOR FONT (Exactly 2 sizes/steps down)
    author_font_size = quote_font_size - 15 
    try:
        author_font = ImageFont.truetype(font_path, author_font_size)
    except:
        author_font = ImageFont.load_default()

    # 3. DRAW QUOTE (Centered slightly higher than the middle)
    draw.multiline_text((540, 450), wrapped_quote, fill=(255, 255, 255), 
                        anchor="mm", align="center", spacing=20, font=quote_font)
    
    # 4. CALCULATE SPACING & DRAW AUTHOR
    # We find where the quote box ends and add a 60px "gap"
    quote_bbox = draw.multiline_textbbox((540, 450), wrapped_quote, font=quote_font, anchor="mm", align="center", spacing=20)
    author_y_position = quote_bbox[3] + 60 
    
    draw.text((540, author_y_position), f"— {author}", fill=(200, 200, 200), 
              anchor="mm", font=author_font)

    # 5. BRANDING & GOLD ACCENT (Stable at the bottom)
    try:
        brand_font = ImageFont.truetype(font_path, 35)
        draw.text((540, 960), "www.AlexSellsCT.com", fill=(120, 120, 120), anchor="mm", font=brand_font)
    except:
        draw.text((540, 960), "www.AlexSellsCT.com", fill=(120, 120, 120), anchor="mm")

    draw.line([(420, 910), (660, 910)], fill=(212, 175, 55), width=6)
    
    # Save for Preview Artifact & LinkedIn
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
    
    # 🎯 AUTOMATED CTA LOGIC
    # It checks the JSON first, then falls back to this general professional one
    default_cta = "Success is built on better systems and consistent execution. Let's connect and grow together."
    cta_text = quote_data.get('cta', default_cta)

    post_payload = {
        "author": AUTHOR_URN,
        "commentary": (
            f"💡 Insight of the Week:\n\n"
            f"\"{quote_data['text']}\"\n\n"
            f"— {quote_data['author']}\n\n"
            f"🎯 {cta_text}\n\n"
            "--------------------------\n"
            "Alex Teplitskiy | REALTOR | Century21 AllPoints\n"
            "📞 (860) 543-9417 | 🌐 www.AlexSellsCT.com\n"
            "✉️ alexteplitskiy@gmail.com\n\n"
            "#Motivation #RealEstate #Systems #WestHartford"
        ),
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
    post_to_linkedin()
    # Manually trigger the image creation so you get your Artifact
'''
    with open('quotes.json', 'r') as f:
        quotes = json.load(f)
    quote_data = next((q for q in quotes if not q.get('posted')), None)
    if quote_data:
        create_quote_image(quote_data['text'], quote_data['author'])
        print("Preview image created! Check GitHub Artifacts.")
'''
