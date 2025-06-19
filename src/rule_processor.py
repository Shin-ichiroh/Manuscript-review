import os
import re # For parsing

def load_rulebook(filepath: str = "rulebook.md") -> str:
    """
    Loads the rulebook content from the given filepath.
    """
    try:
        if not os.path.isabs(filepath) and os.path.dirname(__file__):
            base_dir = os.path.dirname(__file__)
            if filepath == "rulebook.md":
                filepath = os.path.join(base_dir, "..", filepath)
            else:
                filepath = os.path.join(base_dir, filepath)

        normalized_filepath = os.path.normpath(filepath)

        with open(normalized_filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"Error: Rulebook file not found at '{normalized_filepath}'."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def parse_rulebook_to_chunks(rulebook_content: str) -> list[dict[str, str]]:
    """
    Parses the rulebook content into a list of rule chunks.
    Each chunk is a dictionary with 'main_item_title' and 'rule_text'.
    """
    chunks = []
    current_main_item_title = None
    current_rule_lines = []

    main_item_regex = re.compile(r"^\s*##\s*大項目\d+：(.+)")
    rule_start_regex = re.compile(r"^\s*(\*|\-|\d+\.)\s+.*")

    def clean_text(text: str) -> str:
        return re.sub(r'\s+', ' ', text.strip())

    def store_current_rule():
        nonlocal current_rule_lines
        if current_rule_lines and current_main_item_title:
            raw_text = "\n".join(line.strip() for line in current_rule_lines).strip()
            processed_text = re.sub(r'[ \t]+', ' ', raw_text)
            processed_text = "\n".join(line.lstrip() for line in processed_text.split('\n'))
            chunks.append({
                'main_item_title': current_main_item_title,
                'rule_text': processed_text
            })
            current_rule_lines = []

    lines = rulebook_content.splitlines()

    for line in lines:
        if not line.strip():
            continue

        main_item_match = main_item_regex.match(line)

        if line.strip().startswith("###"):
            if current_rule_lines:
                 store_current_rule()
            current_main_item_title = None
            continue

        if main_item_match:
            store_current_rule()
            current_main_item_title = main_item_match.group(1).strip()
        elif current_main_item_title:
            is_new_rule_point = line.lstrip().startswith(('*', '-', '1.','2.','3.','4.','5.','6.','7.','8.','9.','10.','11.','12.')) or \
                               (not current_rule_lines and line.strip())

            if is_new_rule_point and line.strip().startswith(("*", "-")):
                 if current_rule_lines:
                    store_current_rule()
                 current_rule_lines.append(line.strip())
            elif line.lstrip().startswith(tuple(f"{i}." for i in range(1, 13))):
                if current_rule_lines and not line.startswith(" " * (len(current_rule_lines[-1]) - len(current_rule_lines[-1].lstrip()) + 1)):
                    store_current_rule()
                current_rule_lines.append(line.strip())
            elif current_rule_lines:
                current_rule_lines.append(line.strip())
            elif line.strip() and current_main_item_title:
                store_current_rule()
                current_rule_lines.append(line.strip())

    store_current_rule()
    return chunks

def get_mock_vector(text: str) -> list[float]:
    """
    Generates a mock vector for the given text.
    The vector is 10-dimensional, based on ASCII values of the first 10 chars.
    """
    # Pad with spaces if text is shorter than 10 chars
    padded_text = text[:10].ljust(10, ' ')
    return [float(ord(c)) for c in padded_text]

def add_mock_vectors_to_chunks(chunks: list[dict[str, str]]) -> list[dict[str, any]]:
    """
    Adds a mock vector to each chunk in the list.
    The input type for chunks is list[dict[str, str]],
    the output type is list[dict[str, str | list[float]]] but using `any` for simplicity here.
    """
    vectorized_chunks = []
    for chunk in chunks:
        # Create a new dictionary to avoid modifying the original chunk in place if it's not desired
        # or directly modify chunk: chunk['vector'] = ...
        new_chunk = chunk.copy() # Make a shallow copy
        new_chunk['vector'] = get_mock_vector(chunk['rule_text'])
        vectorized_chunks.append(new_chunk)
    return vectorized_chunks

if __name__ == "__main__":
    rulebook_path_from_src = "../rulebook.md"

    print("Attempting to load rulebook...")
    content = load_rulebook(rulebook_path_from_src)

    if content.startswith("Error:") or content.startswith("An unexpected error occurred:"):
        print(content)
    else:
        print(f"Rulebook loaded successfully. Total length: {len(content)} characters.")

        print("\nParsing rulebook to chunks...")
        parsed_chunks = parse_rulebook_to_chunks(content)
        print(f"Found {len(parsed_chunks)} chunks.")

        print("\nAdding mock vectors to chunks...")
        vectorized_chunks = add_mock_vectors_to_chunks(parsed_chunks)
        print(f"Processed {len(vectorized_chunks)} chunks with mock vectors.")

        print("\nFirst chunk with vector:")
        if vectorized_chunks:
            first_chunk_with_vector = vectorized_chunks[0]
            print(f"Main Item Title: {first_chunk_with_vector['main_item_title']}")
            print(f"Rule Text:\n{first_chunk_with_vector['rule_text']}")
            print(f"Mock Vector: {first_chunk_with_vector['vector']}")
        else:
            print("No chunks were processed.")
