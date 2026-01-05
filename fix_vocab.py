import os

vocab_path = "models/f5-tts-czech/vocab.txt"

with open(vocab_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Original line count: {len(lines)}")
print(f"First line repr: {repr(lines[0])}")
print(f"Last line repr: {repr(lines[-1])}")

# Clean up
cleaned_lines = []
seen = set()

# Explicitly handle the "space" token usually at the start
# If the first line is just a newline or space, keep it as ' '
for line in lines:
    # Remove newline char for processing
    content = line.strip('\n').strip('\r')

    # If the line was just a newline, content is empty string.
    # In F5-TTS vocab, a space is usually represented as a literal space character + newline?
    # Or just a line containing a space?
    # User said "first line is space".

    if content == "" and line != "":
        # It might be a space line
        # Check if original line had a space
        if " " in line:
            token = " "
        else:
            token = "" # Empty line?
    else:
        token = content

    # Add to list if unique (and not empty?)
    # F5-TTS vocab usually includes space as a token.
    # If we have duplicate ' ' at end, we skip it.

    if token not in seen:
        # Special case: if token is empty string, do we include it?
        # Usually not, unless it signifies <pad> explicitly?
        # But here we likely want chars.

        # Keep non-empty tokens, OR the space token.
        if token == "" and " " in seen:
            continue # Skip empty lines if we already have space

        cleaned_lines.append(token)
        seen.add(token)

print(f"Unique tokens found: {len(cleaned_lines)}")

# We need exactly 101 tokens.
# Examples from user: Space, !, ", ...
# If we have more, we might need to trim.
# If we have fewer, we have a problem.

if len(cleaned_lines) > 101:
    print(f"Warning: Finding {len(cleaned_lines)} unique tokens, trimming to 101 to match checkpoint.")
    cleaned_lines = cleaned_lines[:101]
elif len(cleaned_lines) < 101:
    print(f"Warning: Only found {len(cleaned_lines)} unique tokens. Checkpoint expects 101.")

with open(vocab_path, "w", encoding="utf-8") as f:
    for i, token in enumerate(cleaned_lines):
        # Write token + newline (except maybe last one? standard is newline)
        f.write(token + "\n")

print(f"Wrote {len(cleaned_lines)} tokens to {vocab_path}")
