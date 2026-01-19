
import re

def check_regex(input_text):
    # Old regex
    old_regex = re.compile(r"\b(what'?s new|what'?s happening|anything new|news)\b", re.IGNORECASE)
    # New regex
    new_regex = re.compile(r"\b(what'?s new|what'?s happening|anything new)\b", re.IGNORECASE)
    
    print(f"Input: '{input_text}'")
    print(f"Old Match: {bool(old_regex.search(input_text))}")
    print(f"New Match: {bool(new_regex.search(input_text))}")
    print("-" * 20)

check_regex("about major news stories that people are talking about right now")
check_regex("what's new with you?")
check_regex("tell me the news")
