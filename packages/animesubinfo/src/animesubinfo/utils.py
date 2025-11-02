import re

import roman # type: ignore


def normalize(text: str) -> str:
    """
    Normalize text by:
    1. Converting Roman numerals to Arabic numbers
    2. Lowercasing
    3. Removing leading zeros from numbers
    4. Removing spaces and non-alphanumeric characters
    """

    # Step 1: Convert Roman numerals to Arabic
    def replace_roman(match: re.Match[str]) -> str:
        try:
            return str(roman.fromRoman(match.group(0).upper()))
        except roman.InvalidRomanNumeralError:
            return match.group(0)

    # Match Roman numerals as complete words
    text = re.sub(r"\b[IVXLCDM]+\b", replace_roman, text, flags=re.IGNORECASE)

    # Step 2: Lowercase
    text = text.lower()

    # Step 3: Remove leading zeros from numeric prefixes of space-separated tokens
    def process_token(match: re.Match[str]) -> str:
        word = match.group(0)
        if word and word[0].isdigit():
            # Find where digits end
            i = 0
            while i < len(word) and word[i].isdigit():
                i += 1
            # Remove leading zeros from numeric part
            numeric_part = word[:i].lstrip("0") or "0"
            return numeric_part + word[i:]
        return word

    text = re.sub(r"\S+", process_token, text)

    # Step 4: Remove non-alphanumeric characters (including spaces)
    text = re.sub(r"[^a-z0-9]", "", text)

    return text
