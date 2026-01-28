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

  function timeToMillis(timeStr) {
    const parts = timeStr.split(':');
    const secondsParts = parts[2].split('.');
    return (parseInt(parts[0], 10) * 3600 + parseInt(parts[1], 10) * 60 + parseInt(secondsParts[0], 10)) * 1000 + parseInt(secondsParts[1], 10);
  }

  // --- Core: Inject Spans into DOM ---
  function injectCues(rootElement, cues) {
    // 1. Flatten all text nodes
    const textNodes = [];
    const walker = document.createTreeWalker(rootElement, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        if (node.parentElement.closest('#audio-container, .comment-form, .postNav')) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    }, false);

    let node;
    while (node = walker.nextNode()) {
      textNodes.push(node);
    }

    let fullText = "";
    const charMap = [];
    textNodes.forEach(textNode => {
      const val = textNode.nodeValue;
      for (let i = 0; i < val.length; i++) {
        charMap.push({ node: textNode, index: i });
      }
      fullText += val;
    });

    // --- Normalization ---
    function robustNormalize(char) {
      if (/\s/.test(char)) return ' ';
      if (['’', '‘'].includes(char)) return "'";
      if (['“', '”'].includes(char)) return '"';
      if (['–', '—'].includes(char)) return '-';
      return char.toLowerCase();
    }

    const normalizedData = (function buildNormalized(rawText) {
      let norm = "";
      const mapping = [];
      for (let i = 0; i < rawText.length; i++) {
        let char = rawText[i];
        if (char === '…') {
          for (let j = 0; j < 3; j++) { mapping.push(i); norm += "."; }
          continue;
        }
        const nChar = robustNormalize(char);
        if (nChar === ' ' && (norm.length === 0 || norm[norm.length - 1] === ' ')) continue;
        mapping.push(i);
        norm += nChar;
      }
      return { str: norm, map: mapping };
    })(fullText);

    function normalizeCue(text) {
      let res = "";
      for (const char of text) {
        if (char === '…') { res += "..."; continue; }
        const n = robustNormalize(char);
        if (n === ' ' && (res.length === 0 || res[res.length - 1] === ' ')) continue;
        res += n;
      }
      return res.trim();
    }

    const normParams = normalizedData;
    let lastFoundIndex = 0;
    const matches = []; // { cue, rawStart, rawEnd }
    const missingCues = [];

    cues.forEach(cue => {
      const cueText = normalizeCue(cue.text);
      if (!cueText) return;

      const searchStr = normParams.str;
      let foundNormIndex = searchStr.indexOf(cueText, lastFoundIndex);

      // Fuzzy match for "Published on [Date]" metadata
      if (foundNormIndex === -1 && cueText.startsWith("published on ")) {
        let fuzzyCue = cueText.replace("published on ", "").trim();
        // Remove trailing dot if exists
        if (fuzzyCue.endsWith(".")) fuzzyCue = fuzzyCue.slice(0, -1);
        foundNormIndex = searchStr.indexOf(fuzzyCue, lastFoundIndex);
      }

      if (foundNormIndex !== -1) {
        const startNorm = foundNormIndex;
        const endNorm = foundNormIndex + (cueText.startsWith("published on ") && cueText.indexOf(searchStr.substr(foundNormIndex, 10)) === -1 ? (cueText.length - 13) : cueText.length);

        // Actually, let's keep it simple: the match length is whatever we found in searchStr
        // But indexOf doesn't tell us length if we fuzzy matched.
        // Let's just use the actual cueText length or the fuzzy length.
        let matchLength = cueText.length;
        if (cueText.startsWith("published on ") && searchStr.indexOf(cueText, lastFoundIndex) === -1) {
          // We used fuzzy
          let fuzzyCue = cueText.replace("published on ", "").trim();
          if (fuzzyCue.endsWith(".")) fuzzyCue = fuzzyCue.slice(0, -1);
          matchLength = fuzzyCue.length;
        }

        const rawStart = normParams.map[startNorm];
        let rawEnd = (startNorm + matchLength - 1 < normParams.map.length) ? normParams.map[startNorm + matchLength - 1] + 1 : fullText.length;

        lastFoundIndex = startNorm + matchLength;
        matches.push({ cue, rawStart, rawEnd });
      } else {
        missingCues.push(cue.text);
      }
    });

    // 2. Identify and execute wraps (Reverse order to avoid invalidating indices)
    // Actually, we need to handle block-crossing by splitting matches into "Safe Ranges"
    const safeMatches = [];
    matches.forEach(m => {
      let currentStart = m.rawStart;
      for (let i = m.rawStart; i < m.rawEnd; i++) {
        const node = charMap[i].node;
        const prevNode = i > m.rawStart ? charMap[i - 1].node : null;

        if (prevNode && node !== prevNode) {
          // Check if we crossed a block-level boundary
          if (areSeparatedByBlock(prevNode, node)) {
            safeMatches.push({ cue: m.cue, start: currentStart, end: i });
            currentStart = i;
          }
        }
      }
      safeMatches.push({ cue: m.cue, start: currentStart, end: m.rawEnd });
    });

    function areSeparatedByBlock(node1, node2) {
      // Find the parent block of each node
      const getBlock = (n) => n.parentElement.closest('p, div, li, h1, h2, h3, h4, h5, h6, article, section, figure');
      return getBlock(node1) !== getBlock(node2);
    }

    // Sort by start position descending
    safeMatches.sort((a, b) => b.start - a.start);

    safeMatches.forEach(m => {
      if (m.start >= m.end) return;

      try {
        const range = document.createRange();
        const startObj = charMap[m.start];
        const endObj = charMap[m.end - 1];

        range.setStart(startObj.node, startObj.index);
        range.setEnd(endObj.node, endObj.index + 1);

        const span = document.createElement('span');
        span.className = 'hyperaudio-transcript-text unread';
        span.setAttribute('data-m', m.cue.start);
        span.setAttribute('data-d', m.cue.duration);

        const contents = range.extractContents();
        span.appendChild(contents);
        range.insertNode(span);
      } catch (e) {
        // Silent
      }
    });

    if (missingCues.length > 0) {
      console.warn(`[VTT Injector] Missing ${missingCues.length} cues:`, missingCues);
    }
    console.log(`[VTT Injector] Injected (DOM) ${matches.length} / ${cues.length} matches.`);
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
