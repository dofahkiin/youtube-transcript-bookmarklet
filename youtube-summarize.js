javascript: (async function(){
  
  async function fetchTranscript() {
    const rawData =
      window.ytInitialPlayerResponse ||
      window.ytplayer?.config?.args?.raw_player_response;
    
    if (!rawData) {
      throw new Error("No transcript found (missing YouTube config).");
    }
    
    const captionTracks =
      rawData.captions?.playerCaptionsTracklistRenderer?.captionTracks;
    if (!captionTracks?.length) {
      throw new Error("No caption tracks available.");
    }

    const track = captionTracks.find(t => t.kind === "asr") || captionTracks[0];
    if (!track?.baseUrl) {
      throw new Error("No valid caption track found.");
    }

    const response = await fetch(track.baseUrl);
    const xml = await response.text();
    const matches = xml.match(/<text[^>]*>([^<]+)/g) || [];
    const lines = matches.map(m => m.replace(/<text[^>]*>/, "")).join("\n");
    return lines;
  }

  async function getSummaryFromDeepSeek(transcript) {
    
    const messages = [
      { role: "system", content: "You are a helpful assistant that summarizes text." },
      { 
        role: "user", 
        content: `Summarize the following text to ~100 words:\n\n${transcript}` 
      }
    ];

    const truncated = messages[1].content.slice(0, 12000); 
    messages[1].content = truncated;

    const body = {
      model: "deepseek-chat",
      messages,
    };

    const res = await fetch("https://api.deepseek.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR-API-HERE"
      },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`DeepSeek API error: ${res.status} - ${errorText}`);
    }

    const data = await res.json();
    return data.choices?.[0].message?.content || "No summary found.";
  }

  try {
    
    const transcript = await fetchTranscript();
    const summary = await getSummaryFromDeepSeek(transcript);    
    try {
      await navigator.clipboard.writeText(summary);
      alert(`Summary (copied to clipboard):\n\n${summary}`);
    } catch (err) {
      
      alert("Summary:\n\n" + summary);
    }

  } catch (err) {
    alert(`Error: ${err.message}`);
    console.error(err);
  }
})();
