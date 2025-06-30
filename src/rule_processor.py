import os
import re # For parsing

def load_rulebook(filepath: str = "rulebook.md") -> str:
    """
    Loads the rulebook content from the given filepath.
    """
    try:
        script_dir = os.path.dirname(__file__)
        if filepath == "rulebook.md":
            normalized_filepath = os.path.normpath(os.path.join(script_dir, "..", filepath))
        elif not os.path.isabs(filepath):
            normalized_filepath = os.path.normpath(os.path.join(script_dir, "..", filepath))
        else:
            normalized_filepath = filepath

        with open(normalized_filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"Error: Rulebook file not found at '{normalized_filepath}'. Check path relative to project root or provide absolute path."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def parse_rulebook_to_chunks(rulebook_content: str) -> list[dict[str, str]]:
    """
    Parses the rulebook content into chunks, prioritizing ###SPLIT### markers.
    """
    chunks = []
    current_main_item_title = None
    current_rule_lines = [] # Stores raw lines for the current accumulating chunk

    main_item_regex = re.compile(r"^\s{4}##\s*大項目\d+：(.+)")
    # Regex for split markers, capturing any text on the same line *after* the marker.
    split_marker_regex = re.compile(r"^\s*(?:###SPLIT###|##SPLIT##)\s*(.*)")

    # These headers are not part of any chunk and reset context.
    ignored_headers_regex = re.compile(r"^\s*###\s*(あなた|手順|審査ポイント詳細)")
    # These lines are descriptive but not rules themselves, effectively ignored unless part of a multi-line chunk.
    # For the new strategy, if they are not preceded by a SPLIT marker, they'll be part of the current chunk.
    # If we want them strictly ignored, they need to be handled explicitly before accumulation.
    # For now, this regex is more for context.
    # descriptive_lines_regex = re.compile(r"^\s*(手順にある、大項目１～大項目８の中に更に詳細のチェックポイントを記載しています。|・ 大項目の中の詳細チェックポイントごとに|また参考資料として)")


    def finalize_chunk():
        nonlocal current_rule_lines, current_main_item_title
        if current_rule_lines and current_main_item_title:
            cleaned_lines = []
            for l_orig in current_rule_lines:
                stripped_l = l_orig.strip()
                if stripped_l: # Only consider lines with actual content after stripping
                    condensed_l = re.sub(r' +', ' ', stripped_l)
                    cleaned_lines.append(condensed_l)

            full_rule_text = "\n".join(cleaned_lines).strip()

            if full_rule_text:
                chunks.append({
                    'main_item_title': current_main_item_title,
                    'rule_text': full_rule_text
                })
        current_rule_lines = []

    lines = rulebook_content.splitlines()

    for line_number, line in enumerate(lines):
        # Important: Check for ignored headers first as they reset context
        if ignored_headers_regex.match(line):
            finalize_chunk()
            current_main_item_title = None # This line is a global header, not under any 大項目
            continue # Move to next line

        main_item_match = main_item_regex.match(line)
        split_match = split_marker_regex.match(line)

        if main_item_match:
            finalize_chunk() # Finalize previous 大項目's last chunk
            current_main_item_title = main_item_match.group(1).strip()
            # current_rule_lines is already reset by finalize_chunk.
            # The 大項目 line itself doesn't start content for current_rule_lines.
        elif split_match:
            finalize_chunk() # Finalize the chunk before this ###SPLIT###
            # current_rule_lines is already reset.
            # Add text *after* the split marker to the new chunk, if any.
            text_after_split = split_match.group(1).strip()
            if text_after_split:
                if current_main_item_title: # Only add if we are under a main title
                    current_rule_lines.append(text_after_split)
                # If no current_main_item_title, this text is effectively orphaned (should not happen with current rulebook structure)
        else:
            # This line is not a main item title, not a split marker, and not an ignored global header.
            # It's content that belongs to the current chunk being accumulated.
            stripped_content = line.strip()
            if stripped_content: # Only add non-empty lines
                if current_main_item_title: # Ensure we are under a 大項目
                    # If current_rule_lines is empty, this is the first line of a new chunk (e.g. after a 大項目 title or after a line with just ###SPLIT###)
                    current_rule_lines.append(line) # Append raw line; finalize_chunk will strip.
                # Else: This line is before any 大項目, so ignore it.

    finalize_chunk() # Store the last accumulated rule
    return chunks


def get_mock_vector(text: str) -> list[float]:
    padded_text = text[:10].ljust(10, ' ')
    return [float(ord(c)) for c in padded_text]

def add_mock_vectors_to_chunks(chunks: list[dict[str, str]]) -> list[dict[str, any]]:
    vectorized_chunks = []
    for chunk in chunks:
        new_chunk = chunk.copy()
        new_chunk['vector'] = get_mock_vector(chunk['rule_text'])
        vectorized_chunks.append(new_chunk)
    return vectorized_chunks

if __name__ == "__main__":
    rulebook_filepath = "rulebook.md"
    print(f"Attempting to load rulebook from: {rulebook_filepath}")
    content = load_rulebook(rulebook_filepath)

    if content.startswith("Error:") or content.startswith("An unexpected error occurred:"):
        print(content)
    else:
        print(f"Rulebook loaded successfully. Total length: {len(content)} characters.")

        print("\nParsing rulebook to chunks (new strategy)...")
        parsed_chunks = parse_rulebook_to_chunks(content)
        print(f"\nFound {len(parsed_chunks)} chunks.\n")

        print("--- All Parsed Chunks (New Strategy) ---")
        for i, chunk in enumerate(parsed_chunks):
            print(f"--- Chunk {i} ---")
            print(f"  Main Item Title: {chunk['main_item_title']}")
            print(f"  Rule Text:\n{chunk['rule_text']}")
            print("--------------------\n")
