import sys
import requests
import re
import json

DEEPSEEK_API_KEY = "Bearer YOUR-API-KEY"  # e.g. "Bearer sk-xxxx..."

def fetch_transcript(video_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    resp = requests.get(video_url, headers=headers)
    resp.raise_for_status()
    html = resp.text

    # Extract ytInitialPlayerResponse JSON
    match = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.*?\});', html)
    if not match:
        raise ValueError("No transcript found (missing ytInitialPlayerResponse).")

    json_str = match.group(1)
    data = json.loads(json_str)

    # Get caption track
    captions = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {})
    caption_tracks = captions.get("captionTracks", [])
    if not caption_tracks:
        raise ValueError("No caption tracks available for this video.")

    track = next((t for t in caption_tracks if t.get("kind") == "asr"), caption_tracks[0])
    if not track or "baseUrl" not in track:
        raise ValueError("No valid caption track found.")

    # Fetch transcript XML
    transcript_resp = requests.get(track["baseUrl"], headers=headers)
    transcript_resp.raise_for_status()
    xml = transcript_resp.text

    # Extract text from <text ...>...</text>
    lines = []
    for m in re.finditer(r'<text[^>]*>([^<]+)', xml):
        lines.append(m.group(1))

    return "\n".join(lines)

def stream_summary_from_deepseek(transcript, model="deepseek-chat"):
    """
    Attempt a streaming request to the DeepSeek API. 
    This only works if DeepSeek supports streaming in a manner similar to OpenAI.
    """
    # Truncate large transcripts
    truncated_text = transcript[:12000]

    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes text."},
        {
            "role": "user",
            "content": f"Summarize this text to ~100 words:\n\n{truncated_text}"
        }
    ]

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": DEEPSEEK_API_KEY
    }

    # The body includes stream: true, hoping DeepSeek supports it
    body = {
        "model": model,
        "messages": messages,
        "stream": True
    }

    # Note 'stream=True' in 'requests.post' so we can iterate lines as they arrive
    resp = requests.post(url, headers=headers, json=body, stream=True)
    if not resp.ok:
        error_txt = resp.text
        raise ValueError(f"DeepSeek API error {resp.status_code} - {error_txt}")

    # Now read the response line by line
    partial_summary = []
    for line in resp.iter_lines(delimiter=b"\n"):
        if line:
            decoded_line = line.decode("utf-8")
            # Some streaming APIs send lines that start with data: ...
            # Typically the format might be: `data: {...}`
            # Let's just parse if it looks like JSON
            if decoded_line.startswith("data:"):
                payload_str = decoded_line[len("data:"):].strip()
                if payload_str == "[DONE]":
                    # indicates the stream is over
                    break
                try:
                    payload = json.loads(payload_str)
                    # For OpenAI style: there's often a 'choices' -> 'delta' -> 'content'
                    # Or 'choices[].delta.content'
                    # We'll guess DeepSeek is similar, but you may have to adjust the path
                    choices = payload.get("choices", [])
                    if choices:
                        delta_content = choices[0].get("delta", {}).get("content", "")
                        # Accumulate partial content
                        if delta_content:
                            partial_summary.append(delta_content)
                            # Print without a newline, to simulate streaming
                            sys.stdout.write(delta_content)
                            sys.stdout.flush()
                except json.JSONDecodeError:
                    # It's possible some lines are just empty or have event info
                    pass

    print()  # final newline after streaming is done
    return "".join(partial_summary)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 youtube_summarizer.py <youtube_url>")
        sys.exit(1)

    video_url = sys.argv[1]
    try:
        transcript = fetch_transcript(video_url)
        print("Transcript fetched, starting streaming summary...\n")
        full_summary = stream_summary_from_deepseek(transcript)
        # print("\n===== FINAL SUMMARY =====\n")
        # print(full_summary)
        # print("\n=========================\n")
    except Exception as e:
        print("Error:", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
