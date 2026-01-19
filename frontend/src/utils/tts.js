// Lightweight Text-to-Speech helper used across Agent Amigos UI.
// Uses the browser Web Speech API (SpeechSynthesis).

const STORAGE_KEY = "amigos-voice-enabled";

export function getVoiceEnabled(defaultValue = true) {
  try {
    const stored = window?.localStorage?.getItem(STORAGE_KEY);
    return stored !== null ? JSON.parse(stored) : defaultValue;
  } catch {
    return defaultValue;
  }
}

export function setVoiceEnabled(enabled) {
  try {
    window?.localStorage?.setItem(STORAGE_KEY, JSON.stringify(!!enabled));
  } catch {
    // ignore
  }
}

export function primeVoices() {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  const loadVoices = () => {
    try {
      window.speechSynthesis.getVoices();
    } catch {
      // ignore
    }
  };
  loadVoices();
  try {
    window.speechSynthesis.onvoiceschanged = loadVoices;
  } catch {
    // ignore
  }
}

export function unlockSpeechSynthesisOnFirstGesture() {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  const unlock = () => {
    try {
      const u = new SpeechSynthesisUtterance(" ");
      u.volume = 0;
      window.speechSynthesis.speak(u);
      window.speechSynthesis.cancel();
    } catch {
      // ignore
    }
  };

  try {
    window.addEventListener("pointerdown", unlock, { once: true });
  } catch {
    // ignore
  }

  return () => {
    try {
      window.removeEventListener("pointerdown", unlock);
    } catch {
      // ignore
    }
  };
}

function cleanForSpeech(text) {
  if (!text) return "";
  return String(text)
    .replace(/[*_~`#]/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/<[^>]*>/g, "")
    .replace(
      /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}]/gu,
      ""
    )
    .replace(/\s+/g, " ")
    .trim();
}

export function speak(text, { enabled = true, interrupt = true } = {}) {
  if (!enabled) return;
  if (typeof window === "undefined" || !window.speechSynthesis) return;

  const spokenText = cleanForSpeech(text);
  if (!spokenText) return;

  // Skip internal UI noise
  if (
    spokenText.startsWith("[") ||
    spokenText.startsWith("✓") ||
    spokenText.startsWith("⚠")
  ) {
    return;
  }

  try {
    if (interrupt) window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(spokenText);

    const voices = window.speechSynthesis.getVoices();

    // Simple heuristic to detect Tagalog/Filipino content
    const isTagalog =
      /\b(ang|ng|sa|na|po|opo|hindi|wala|ako|ikaw|siya|tayo|kami|kayo|sila|ni|kay|may|mayroon|magandang|araw|salamat)\b/i.test(
        spokenText
      );

    let preferred = null;

    if (isTagalog) {
      preferred = voices.find(
        (v) =>
          v.lang.includes("fil") ||
          v.lang.includes("tl") ||
          v.name.toLowerCase().includes("filipino") ||
          v.name.toLowerCase().includes("tagalog")
      );
    }

    if (!preferred) {
      preferred =
        voices.find(
          (v) =>
            v.name.toLowerCase().includes("zira") ||
            v.name.toLowerCase().includes("samantha") ||
            v.name.toLowerCase().includes("victoria") ||
            v.name.toLowerCase().includes("hazel") ||
            v.name.toLowerCase().includes("susan") ||
            v.name.includes("Google UK English Female") ||
            v.name.includes("Microsoft Zira")
        ) ||
        voices.find((v) => v.lang?.toLowerCase().startsWith("en")) ||
        null;
    }

    if (preferred) {
      utterance.voice = preferred;
      utterance.lang = preferred.lang;
    } else {
      utterance.lang = "en-US";
    }

    utterance.volume = 1;
    utterance.pitch = 1.0;
    utterance.rate = 0.85;

    window.speechSynthesis.speak(utterance);
  } catch {
    // ignore
  }
}
