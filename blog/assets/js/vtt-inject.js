/**
 * vtt-inject.js
 * 
 * 1. Parses a VTT file.
 * 2. Matches VTT text with text nodes in the target HTML container.
 * 3. Wraps matches in <span> tags with `data-m` (milliseconds) attributes.
 * 4. Initializes HyperaudioLite.
 */

(function () {
  // --- Helper: Parse VTT to Array of Cues ---
  function parseVTT(vttString) {
    const pattern = /(\d{2}:\d{2}:\d{2}\.\d{3})\s-->\s(\d{2}:\d{2}:\d{2}\.\d{3})\n(.*?)(?=\n\n|\n$|$)/gs;
    const cues = [];
    let match;

    while ((match = pattern.exec(vttString)) !== null) {
      cues.push({
        start: timeToMillis(match[1]),
        duration: timeToMillis(match[2]) - timeToMillis(match[1]),
        text: match[3].trim().replace(/\n/g, ' ')
      });
    }
    return cues;
  }

  // --- Helper: Time String to Milliseconds ---
  function timeToMillis(timeStr) {
    const parts = timeStr.split(':');
    const secondsParts = parts[2].split('.');
    return (parseInt(parts[0], 10) * 3600 + parseInt(parts[1], 10) * 60 + parseInt(secondsParts[0], 10)) * 1000 + parseInt(secondsParts[1], 10);
  }

  // --- Helper: Escape Regex Special Characters ---
  function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  // --- Core: Inject Spans into DOM ---
  function injectCues(rootElement, cues) {
    let html = rootElement.innerHTML;
    let matchCount = 0;

    cues.forEach(cue => {
      // 1. Normalize the search text
      // 1. Normalize the search text
      let safeText = escapeRegExp(cue.text);

      // Use placeholders to protect quote regex patterns from being decorated as punctuation
      const SQ_PH = "___SQ___";
      const DQ_PH = "___DQ___";
      safeText = safeText.replace(/['’]/g, SQ_PH);
      safeText = safeText.replace(/["“”]/g, DQ_PH);

      // 2. Handle HTML tags between words and punctuation (The Fix)
      const flexibleSpacer = '(?:\\s+|<[^>]+>)+';

      // Split logic: explicitly handle punctuation to allow tags before it
      // Punctuation: . , ; : ? ! ) ] } " '
      const roughWords = safeText.split(/\s+/);
      const refinedWords = roughWords.map(word => {
        // Fix: Allow punctuation to be optionally escaped (e.g. \. vs ,)
        return word.replace(/(\\)?([.,;?!:)\]}"'])/g, '(?:\\s*<[^>]+>\\s*)*$1$2');
      });

      let regexPattern = refinedWords.join(flexibleSpacer);

      // 3. Restore quote regex patterns
      regexPattern = regexPattern.replace(new RegExp(SQ_PH, 'g'), "['’]");
      regexPattern = regexPattern.replace(new RegExp(DQ_PH, 'g'), '["“”]');

      try {
        const regex = new RegExp(`(${regexPattern})`, '');
        if (regex.test(html)) {
          html = html.replace(regex, `<span data-m="${cue.start}" data-d="${cue.duration}" class="hyperaudio-transcript-text">$1</span>`);
          matchCount++;
        } else {
          // Suppress warning for title/metadata headers not in body
          // console.warn(`[VTT Injector] Could not match text: "${cue.text.substring(0, 50)}..."`);
        }
      } catch (e) {
        console.warn("[VTT Injector] Regex error for cue:", cue);
      }
    });

    console.log(`[VTT Injector] Injected ${matchCount} / ${cues.length} matches.`);
    rootElement.innerHTML = html;
  }

  // --- Main Init Function ---
  window.initHyperaudioInjection = async function (vttUrl, contentId, playerId) {
    try {
      console.log("[VTT Injector] Starting... Target VTT:", vttUrl);

      const response = await fetch(vttUrl);
      if (!response.ok) throw new Error(`Failed to load VTT: ${response.statusText}`);
      const vttText = await response.text();

      const cues = parseVTT(vttText);
      console.log(`[VTT Injector] Parsed ${cues.length} cues.`);

      const contentEl = document.getElementById(contentId);

      if (contentEl && cues.length > 0) {
        injectCues(contentEl, cues);

        // Initialize Hyperaudio Lite
        // Usage: new HyperaudioLite(transcriptId, mediaId, ...config)
        if (typeof HyperaudioLite !== 'undefined') {
          console.log("[VTT Injector] Initializing HyperaudioLite (class)...");
          new HyperaudioLite(contentId, playerId, false, true, false, false, true);
          console.log("[VTT Injector] Success.");
        } else if (window.hyperaudioLite) {
          console.warn("[VTT Injector] Found window.hyperaudioLite function, trying fallback...");
          window.hyperaudioLite(playerId, contentId, { scroll: true });
        } else {
          console.error("[VTT Injector] ERROR: HyperaudioLite class/library not found.");
        }
      } else {
        console.warn("[VTT Injector] Content element not found or no cues parsed.");
      }
    } catch (e) {
      console.error("[VTT Injector] Error:", e);
    }
  };
})();
