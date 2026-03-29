import os
import re
import json
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from jinja2 import Environment, FileSystemLoader

# Try to use openai package if available (for OpenAI, xAI, Groq, LM Studio, etc.)
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from google import genai
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

CHANNEL_URL = "https://www.youtube.com/@rating/videos"
YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"

def get_channel_id(handle_url):
    """Scrape the channel ID from the YouTube handle page."""
    print(f"Fetching channel ID for {handle_url}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(handle_url, headers=headers)
    response.raise_for_status()

    # Look for the channelId in the page source
    match = re.search(r'"channelId":"(UC[\w-]+)"', response.text)
    if match:
        return match.group(1)
    
    # Fallback to older meta tag
    match = re.search(r'<meta itemprop="identifier" content="(UC[\w-]+)">', response.text)
    if match:
        return match.group(1)
        
    raise ValueError("Could not find Channel ID on the page.")

def get_latest_videos(channel_id, max_videos=5):
    """Get the latest videos from the YouTube channel RSS feed."""
    print(f"Fetching RSS feed for channel: {channel_id}")
    feed_url = YOUTUBE_RSS_URL.format(channel_id)
    response = requests.get(feed_url)
    response.raise_for_status()
    
    # Parse XML
    root = ET.fromstring(response.content)
    ns = {
        'yt': 'http://www.youtube.com/xml/schemas/2015',
        'default': 'http://www.w3.org/2005/Atom'
    }
    
    videos = []
    # Find all entry tags
    for entry in root.findall('default:entry', ns)[:max_videos]:
        video_id = entry.find('yt:videoId', ns).text
        title = entry.find('default:title', ns).text
        published = entry.find('default:published', ns).text
        
        # Keep just the date part YYYY-MM-DD
        date_str = published.split('T')[0]
        
        videos.append({
            'id': video_id,
            'title': title,
            'date': date_str,
            'summary': None # To be filled
        })
        
    return videos

def get_transcript(video_id):
    """Download the transcript for a video."""
    print(f"Fetching transcript for video: {video_id}")
    try:
        # Try to get Arabic first, then English, then auto-generated
        transcript_list = YouTubeTranscriptApi().list(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['ar', 'en']).fetch()
        except Exception:
            # If no manual transcript, get the first automatically generated one
            transcript = transcript_list.find_generated_transcript(['ar', 'en']).fetch()
            
        text = " ".join([item.text for item in transcript])
        return text
    except Exception as e:
        print(f"  -> Error fetching transcript: {e}")
        return ""

def summarize_text(text):
    """Summarize text using an LLM. Prefers Google GenAI, falls back to OpenAI."""
    prompt = f"""
قم بتلخيص نص الفيديو التالي بطريقة منظمة وسهلة القراءة.
استخدم النقاط الرئيسية (Bullet points) وأبرز أهم الأفكار.
اكتب التلخيص باللغة العربية حصراً.
نسّق المخرجات باستخدام HTML (استخدم tags مثل <ul>, <li>, <strong>, <p>).
لا تقم بإضافة أي نص خارج كود الـ HTML.

النص:
{text[:15000]}  # Limit text to avoid context token limits
"""

    # Check for Google Gemini keys
    if HAS_GOOGLE and os.environ.get("GEMINI_API_KEY"):
        print("  -> Summarizing with Google Gemini...")
        client = genai.Client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
        
    # Check for OpenAI (or compatible endpoints like LM Studio)
    if os.environ.get("LLM_API_KEY") or os.environ.get("LLM_BASE_URL"):
        print("  -> Summarizing with OpenAI/Compatible API...")
        api_key = os.environ.get("LLM_API_KEY", "lm-studio")  # OpenAI client requires a non-empty api_key
        base_url = os.environ.get("LLM_BASE_URL") # Optional: e.g. for LM Studio http://localhost:1234/v1
        model_name = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
            
        client = OpenAI(**client_kwargs)
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "أنت مساعد ذكي متخصص في تلخيص مقاطع الفيديو وتقديم نقاط رئيسية واضحة."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  -> Error summarizing with API: {e}")
            return f"<p>{text[:500]}...</p>"

    print("  -> No LLM configured. Returning original text snippet.")
    return f"<p>{text[:500]}...</p>"

def main():
    print("Starting Rating Video Summarizer...")
    
    # 1. Get channel ID
    channel_id = get_channel_id(CHANNEL_URL)
    
    # 2. Get latest videos
    videos = get_latest_videos(channel_id, max_videos=5)
    
    # 3. Process each video
    for video in videos:
        transcript = get_transcript(video['id'])
        if transcript:
            summary_html = summarize_text(transcript)
            
            # Clean up potential markdown formatting wrapping the HTML
            summary_html = summary_html.replace("```html", "").replace("```", "").strip()
            video['summary'] = summary_html
        else:
            video['summary'] = "<p style='color:#e50914;'>عذراً، لم نتمكن من العثور على ترجمة/نص لهذا الفيديو لتلخيصه.</p>"
            
    # 4. Generate HTML File
    print("Generating HTML...")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(project_root, 'templates')
    
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('index.html')
    
    # Formatting the required context variables
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    output_html = template.render(
        videos=videos,
        last_updated=now_str
    )
    
    output_path = os.path.join(project_root, 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_html)
        
    print(f"Successfully generated {output_path}!")

if __name__ == "__main__":
    main()
