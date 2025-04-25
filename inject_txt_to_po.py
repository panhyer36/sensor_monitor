import polib
import argparse
import os

def inject_translations(po_file_path, txt_input_path, po_output_path):
    """
    Injects translations from a .txt file into a .po file.
    Assumes the .txt file has one translation per line, corresponding 
    to the non-fuzzy, non-obsolete msgids extracted by extract_po_to_txt.py.
    Handles '\\n' conversion back to newlines.
    """
    try:
        # Load the original .po file
        po = polib.pofile(po_file_path, encoding='utf-8')
        print(f"Loaded original .po file: {po_file_path}")
        
        # Read translations from the .txt file
        with open(txt_input_path, 'r', encoding='utf-8') as f:
            translations = [line.strip() for line in f]
        print(f"Read {len(translations)} translations from: {txt_input_path}")

        # Get target entries from the .po file (same logic as extraction)
        target_entries = []
        for entry in po:
            if not entry.obsolete and not entry.fuzzy and entry.msgid:
                target_entries.append(entry)

        # Check if the number of translations matches the number of target entries
        if len(translations) != len(target_entries):
            print(f"Error: Mismatch in counts! Found {len(target_entries)} target entries in .po file, but {len(translations)} lines in .txt file.")
            print("Please ensure the .txt file corresponds exactly to the extracted msgids.")
            return

        # Inject translations
        injected_count = 0
        for entry, translation in zip(target_entries, translations):
            # Convert literal '\n' back to newline characters
            processed_translation = translation.replace('\\n', '\n')
            entry.msgstr = processed_translation
            # Optionally, remove fuzzy flag if you are confident in the translation
            # if 'fuzzy' in entry.flags:
            #     entry.flags.remove('fuzzy')
            injected_count += 1

        print(f"Injected {injected_count} translations.")
        
        # Save the updated .po file
        po.save(po_output_path)
        print(f"Successfully saved updated .po file to: {po_output_path}")

    except FileNotFoundError:
        print(f"Error: Input file not found. Check paths: {po_file_path}, {txt_input_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject translations from a .txt file into a .po file.")
    parser.add_argument("po_file", help="Path to the original .po file.")
    parser.add_argument("txt_file", help="Path to the input .txt file containing translations.")
    parser.add_argument("output_po_file", help="Path to save the updated .po file.")
    
    args = parser.parse_args()

    # Basic validation
    if not os.path.exists(args.po_file):
         print(f"Error: Input .po file does not exist: {args.po_file}")
    elif not os.path.exists(args.txt_file):
         print(f"Error: Input .txt file does not exist: {args.txt_file}")
    elif not args.po_file.lower().endswith('.po'):
        print(f"Error: Input file does not seem to be a .po file: {args.po_file}")
    elif not args.txt_file.lower().endswith('.txt'):
         print(f"Warning: Input translation file does not have a .txt extension: {args.txt_file}")
         inject_translations(args.po_file, args.txt_file, args.output_po_file)
    elif not args.output_po_file.lower().endswith('.po'):
         print(f"Warning: Output file does not have a .po extension: {args.output_po_file}")
         inject_translations(args.po_file, args.txt_file, args.output_po_file)
    else:
        inject_translations(args.po_file, args.txt_file, args.output_po_file)

# Example Usage:
# python inject_txt_to_po.py locale/zh_Hans/LC_MESSAGES/django.po translated_output.txt locale/zh_Hans/LC_MESSAGES/django_translated.po 