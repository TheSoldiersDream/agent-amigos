// Lightweight Speech-to-Text helper using Web Speech API
// Created for Agent Amigos

export const isSpeechRecognitionSupported = () => {
  return (
    typeof window !== "undefined" &&
    (!!window.SpeechRecognition || !!window.webkitSpeechRecognition)
  );
};

export const startListening = ({
  onResult,
  onStart,
  onEnd,
  onError,
  continuous = false,
  lang = "en-US",
}) => {
  if (!isSpeechRecognitionSupported()) {
    onError?.(new Error("Speech recognition not supported"));
    return null;
  }

  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();

  recognition.continuous = continuous;
  recognition.interimResults = true; // We want to see what we're saying
  recognition.lang = lang;

  let finalTranscript = "";

  recognition.onstart = () => {
    onStart?.();
  };

  recognition.onresult = (event) => {
    let interimTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript;
      } else {
        interimTranscript += event.results[i][0].transcript;
      }
    }
    // Return the current full text (final + interim)
    onResult?.(finalTranscript + interimTranscript, finalTranscript);
  };

  recognition.onerror = (event) => {
    onError?.(event.error);
  };

  recognition.onend = () => {
    onEnd?.();
  };

  try {
    recognition.start();
    return recognition;
  } catch (e) {
    onError?.(e);
    return null;
  }
};
