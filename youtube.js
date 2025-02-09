javascript:(async function(){
  async function getYouTubeTranscript() {
    try {
      
      const rawData =
        window.ytInitialPlayerResponse ||
        window.ytplayer?.config?.args?.raw_player_response;
      
      if (!rawData) {
        alert("No transcript found (missing YouTube config).");
        return;
      }
      
      
      const captionTracks =
        rawData.captions?.playerCaptionsTracklistRenderer?.captionTracks;
      if (!captionTracks || !captionTracks.length) {
        alert("No caption tracks available.");
        return;
      }

      const track = captionTracks.find(t => t.kind === "asr") || captionTracks[0];
      if (!track?.baseUrl) {
        alert("No valid caption track found.");
        return;
      }

      
      const response = await fetch(track.baseUrl);
      const xml = await response.text();

      
      
      const matches = xml.match(/<text[^>]*>([^<]+)/g) || [];
      const lines = matches
        .map(m => m.replace(/<text[^>]*>/, "")) 
        .join("\n");
      
      
      try {
        await navigator.clipboard.writeText(lines);
      } catch (clipboardErr) {
        console.warn("Clipboard write failed:", clipboardErr);
        alert("Transcript fetched but couldn't copy to clipboard automatically.");
      }
      
      
      const snippet = lines.substring(0, 300);
      alert(
        "Transcript fetched (and copied if allowed):\n\n" +
        snippet + (lines.length > 300 ? "…" : "")
      );
    } catch (err) {
      console.error("Error:", err);
      alert("Error: " + err.message);
    }
  }

  getYouTubeTranscript();
})();
