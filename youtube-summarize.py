import requests
import re
import json

DEEPSEEK_API_KEY = "Bearer YOUR-API-KEY-HERE"  # e.g. "Bearer sk-xxxxxxxx..."

def fetch_transcript(video_url):
    """
    Fetch the YouTube watch page HTML, parse out 'ytInitialPlayerResponse' JSON,
    find a caption track, and return the raw transcript text.
    """
    # 1. Get the watch page HTML
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/109.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(video_url, headers=headers)
    resp.raise_for_status()
    html = resp.text

    # 2. Extract the JSON object:  ytInitialPlayerResponse = {...};
    #    The braces can be huge, so we try a lazy or greedy approach carefully.
    match = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.*?\});', html)
    if not match:
        raise ValueError("No transcript found (missing ytInitialPlayerResponse).")

    json_str = match.group(1)
    data = json.loads(json_str)

    # 3. Get the caption track list
    captions = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {})
    caption_tracks = captions.get("captionTracks", [])
    if not caption_tracks:
        raise ValueError("No caption tracks available for this video.")

    # Find an 'asr' track or fallback to the first
    track = next((t for t in caption_tracks if t.get("kind") == "asr"), caption_tracks[0])
    if not track or "baseUrl" not in track:
        raise ValueError("No valid caption track found.")

    # 4. Fetch the caption track (XML)
    transcript_resp = requests.get(track["baseUrl"], headers=headers)
    transcript_resp.raise_for_status()
    xml = transcript_resp.text

    # 5. Extract text between <text ...> ... </text> using RegEx
    lines = []
    for m in re.finditer(r'<text[^>]*>([^<]+)', xml):
        lines.append(m.group(1))

    transcript = "\n".join(lines)
    return transcript

def summarize_with_deepseek(text, model="deepseek-chat"):
    """
    Send the transcript text to DeepSeek with a prompt to summarize it.
    Returns the summary text.
    """
    # Truncate if huge (avoid max token issues)
    truncated = text[:12000]

    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes text."},
        {
            "role": "user",
            "content": f"Summarize the following text to ~100 words:\n\n{truncated}"
        }
    ]

    body = {
        "model": model,
        "messages": messages
    }

    # 1. Make POST request to DeepSeek
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": DEEPSEEK_API_KEY
        },
        json=body
    )
    # 2. Raise if not 2xx
    if not resp.ok:
        raise ValueError(f"DeepSeek API error {resp.status_code} - {resp.text}")

    data = resp.json()
    # 3. Extract the summary from the response
    summary = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return summary if summary else "No summary found."

def main():
    # Example usage:
    video_url = input("Enter a YouTube video URL: ").strip()
    try:
        transcript = fetch_transcript(video_url)
        print("Transcript fetched! Now summarizing...")
        summary = summarize_with_deepseek(transcript)
        print("\n== SUMMARY ==\n")
        print(summary)
        print("\n=============\n")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
