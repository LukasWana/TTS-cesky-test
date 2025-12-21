import sys
import os
sys.path.append(os.getcwd())
from backend.czech_text_processor import get_czech_text_processor

processor = get_czech_text_processor()
word = "led"
print(f"Input: {word}")
chars = list(word)
print(f"Chars initial: {chars}")

# Simulate step 1
last_char = chars[-1].lower()
print(f"last_char: {last_char}")
if last_char in processor.to_neznele:
    print(f"to_neznele[{last_char}]: {processor.to_neznele[last_char]}")
    chars[-1] = processor.to_neznele[last_char]
print(f"Chars after step 1: {chars}")

# Simulate step 2
n = len(chars)
for j in range(n - 2, -1, -1):
    curr = chars[j].lower()
    nxt = chars[j+1].lower()
    print(f"j={j}, curr={curr}, nxt={nxt}")
    if nxt in processor.neznele or nxt == "ch":
        if curr in processor.to_neznele:
            chars[j] = processor.to_neznele[curr]
    elif nxt in processor.znele:
        if curr in processor.to_znele:
            chars[j] = processor.to_znele[curr]
print(f"Chars after step 2: {chars}")
print(f"Final: {''.join(chars)}")

