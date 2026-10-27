import re

# Keywords indicating the user wants to navigate to a specific point in the video
_TEMPORAL_STARTERS = {
    "when",
    "where",
    "find",
    "show",
    "locate",
    "jump",
    "skip",
    "seek",
    "navigate",
    "timestamp",
}

# Phrases indicating the user is looking for a specific section or slide
_TEMPORAL_PHRASES = {
    "what part",
    "what section",
    "what slide",
    "what point",
    "what time",
    "which part",
    "which section",
    "which slide",
    "which minute",
    "the part where",
    "the part about",
    "the section where",
    "the section about",
    "the moment when",
    "the slide with",
    "the slide showing",
    "the slide about",
    "the slide where",
    "where in the",
    "part of the lecture",
    "point in the lecture",
    "at what time",
    "at what point",
    "how long",
    "how far",
    "how many minutes",
    "how early",
    "how late",
    "covered in",
    "go to",
    "slide for",
    "timestamp for",
    "time for",
}

# Phrases indicating the user wants the AI to generate an explanation or summary
_QA_STARTERS = {
    "explain",
    "describe",
    "define",
    "simplify",
    "summarise",
    "summarize",
    "elaborate",
    "clarify",
    "outline",
    "compare",
    "contrast",
    "differentiate",
    "distinguish",
    "list",
    "enumerate",
    "why",
    "who",
    "is",
    "are",
    "does",
    "did",
    "is there",
    "are there",
    "how does",
    "how do",
    "how can",
    "how would",
    "how should",
    "how is",
    "how are",
    "what is",
    "what are",
    "what was",
    "what were",
    "what does",
    "what do",
    "what did",
    "what happens",
    "what happened",
    "what's the",
    "tell me",
    "tell me about",
    "give me",
    "give an",
    "please explain",
    "please describe",
    "please define",
    "please simplify",
    "please summarise",
    "please summarize",
    "please clarify",
    "please elaborate",
    "please walk me through",
    "can you explain",
    "can you describe",
    "can you summarise",
    "can you summarize",
    "could you explain",
    "help me understand",
    "walk me through",
    "break down",
    "i don't understand",
    "i don't get",
}

# Sort QA starters by length descending to match longest multi-word phrases first
_QA_STARTERS_SORTED = sorted(_QA_STARTERS, key=len, reverse=True)


# Route user queries to either the retrieval engine or the QA service based on text heuristics
def classify_query(query: str) -> str:
    q = re.sub(r"\s+", " ", query.strip().lower())
    words = q.split()

    if not words:
        return "retrieval"

    for starter in _QA_STARTERS_SORTED:
        if q.startswith(starter):
            return "qa"

    # single-word queries are keyword searches
    if len(words) == 1:
        return "retrieval"

    if words[0] in _TEMPORAL_STARTERS:
        return "retrieval"

    for phrase in _TEMPORAL_PHRASES:
        if phrase in q:
            return "retrieval"

    if q.endswith("?"):
        return "qa"

    return "retrieval"
