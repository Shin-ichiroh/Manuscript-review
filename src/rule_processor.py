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
    Parses the rulebook content into a list of granular rule chunks.
    Each chunk is a dictionary with 'main_item_title' and 'rule_text'.
    """
    chunks = []
    current_main_item_title = None
    current_rule_lines = []

    main_item_regex = re.compile(r"^\s{4}##\s*大項目\d+：(.+)")
    primary_rule_regex = re.compile(r"^\s{4}[-*]\s+(.*)")
    sub_rule_bullet_regex = re.compile(r"^\s{8}・\s+(.*)")
    # Regex for numbered/lettered list items. Catches prefix like "1.", "(ア)", "a." etc.
    # \s* allows flexible leading spaces before the list marker itself.
    # The main content is captured in group 2. The marker itself is group 1.
    list_item_regex = re.compile(r"^\s*(\([ア-ン一-龠]+\)|[a-zA-Z0-9]+(?:[.。．]))\s*(.*)")


    ignored_headers_regex = re.compile(r"^\s*###\s*(あなた|手順|審査ポイント詳細)")
    ignored_lines_regex = re.compile(r"^\s*(手順にある、大項目１～大項目８の中に更に詳細のチェックポイントを記載しています。|・ 大項目の中の詳細チェックポイントごとに|また参考資料として)")

    def finalize_chunk():
        nonlocal current_rule_lines
        if current_rule_lines and current_main_item_title:
            # Join lines. For cleaning, we'll strip each line then join.
            # The first line in current_rule_lines is the marker line, kept as is.
            # Subsequent lines are continuations.

            # Process first line (marker line)
            first_line = current_rule_lines[0].strip() # Strip marker line

            # Process continuation lines
            continuation_lines_text = ""
            if len(current_rule_lines) > 1:
                # Indent subsequent lines relative to the start of the first actual text part of the marker line
                # This is complex. A simpler way: just strip and join.
                # For now, just strip each continuation line and join with newline
                continuation_lines = [line.strip() for line in current_rule_lines[1:]]
                continuation_lines_text = "\n" + "\n".join(continuation_lines) if continuation_lines else ""

            full_rule_text = (first_line + continuation_lines_text).strip()

            # Condense multiple spaces/tabs within the text to a single space, but preserve newlines.
            full_rule_text = full_rule_text.replace('\t', ' ')
            full_rule_text = re.sub(r' +', ' ', full_rule_text) # Condense spaces
            # This might make multi-line text a single line if not careful.
            # Let's refine: apply space condensing per line if preserving original newlines from list.

            # Re-evaluate cleaning: keep original newlines from current_rule_lines, clean per line.
            cleaned_lines = []
            for i, l in enumerate(current_rule_lines):
                stripped_l = l.strip() # Strip each line
                condensed_l = re.sub(r' +', ' ', stripped_l) # Condense spaces on each line
                cleaned_lines.append(condensed_l)

            full_rule_text = "\n".join(cleaned_lines).strip()


            chunks.append({
                'main_item_title': current_main_item_title,
                'rule_text': full_rule_text
            })
        current_rule_lines = []

    lines = rulebook_content.splitlines()

    for line_number, line in enumerate(lines):
        stripped_line_content = line.strip()
        if not stripped_line_content:
            continue

        if ignored_headers_regex.match(line) or ignored_lines_regex.match(line):
            finalize_chunk()
            current_main_item_title = None
            continue

        main_item_match = main_item_regex.match(line)
        primary_rule_match = primary_rule_regex.match(line)
        sub_rule_bullet_match = sub_rule_bullet_regex.match(line)

        # Adjust list_item_regex to check for sufficient leading whitespace for typical list items
        # This helps differentiate from inline numbers/letters.
        # For example, require at least 8 spaces for something to be a list item if it starts with number/letter.
        is_list_item_candidate = list_item_regex.match(line)
        list_item_match = None
        if is_list_item_candidate:
            # Check indentation level. Example: 8 spaces for (ア), 12 for 1.
            # This regex now checks for EITHER (8+ spaces AND (ア) type marker) OR (10+ spaces AND 1. type marker)
            # This is getting complex, a simpler check might be needed if it overcomplicates.
            # For now, let's use a simpler list_item_regex that includes indentation in its pattern:
            # e.g. ^\s{8,}(\([ア-ン一-龠]+\)|[a-zA-Z0-9]+(?:[.。．]))\s*(.*)
            # Let's simplify the list_item_regex for broader applicability of indentation
            if re.match(r"^\s{8,}", line): # General check for deep indentation for list items
                 list_item_match = is_list_item_candidate # If deeply indented, treat as list_item_match

        is_new_main_item = bool(main_item_match)
        is_new_rule_start = bool(primary_rule_match or sub_rule_bullet_match or list_item_match)

        if is_new_main_item:
            finalize_chunk()
            current_main_item_title = main_item_match.group(1).strip()
        elif current_main_item_title: # Only process if under a main item
            if is_new_rule_start:
                finalize_chunk()
                current_rule_lines.append(line) # Add the raw line, cleaning will be done in finalize_chunk
            elif current_rule_lines: # This line is a continuation
                current_rule_lines.append(line) # Add the raw line
            elif not current_rule_lines and stripped_line_content: # First non-empty, non-marker line after a title
                current_rule_lines.append(line) # Add the raw line

    finalize_chunk()
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
            print(f"  Rule Text:\n{chunk['rule_text']}") # Print raw to see actual multi-line
            print("--------------------\n")
