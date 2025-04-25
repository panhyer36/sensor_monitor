import polib
import argparse
import os

def extract_msgids(po_file_path, txt_output_path):
    """
    Extracts msgid strings from a .po file and writes them to a .txt file.
    Newlines in msgid are replaced with '\\n'.
    Skips fuzzy and obsolete entries, and entries with empty msgid.
    """
    try:
        po = polib.pofile(po_file_path, encoding='utf-8')
        print(f"Loaded .po file: {po_file_path}")
        
        msgids_to_extract = []
        for entry in po:
            if not entry.obsolete and not entry.fuzzy and entry.msgid:
                # Replace newline characters with literal '\n' for storage in txt
                processed_msgid = entry.msgid.replace('\n', '\\n')
                msgids_to_extract.append(processed_msgid)
                
        print(f"Found {len(msgids_to_extract)} non-fuzzy, non-obsolete msgids to extract.")

        with open(txt_output_path, 'w', encoding='utf-8') as f:
            for msgid in msgids_to_extract:
                f.write(msgid + '\n') # Write one msgid per line
                
        print(f"Successfully extracted msgids to: {txt_output_path}")

    except FileNotFoundError:
        print(f"Error: Input .po file not found at {po_file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract msgids from a .po file to a .txt file.")
    parser.add_argument("po_file", help="Path to the input .po file.")
    parser.add_argument("txt_file", help="Path to the output .txt file.")
    
    args = parser.parse_args()
    
    # Basic validation
    if not os.path.exists(args.po_file):
         print(f"Error: Input .po file does not exist: {args.po_file}")
    elif not args.po_file.lower().endswith('.po'):
        print(f"Error: Input file does not seem to be a .po file: {args.po_file}")
    elif not args.txt_file.lower().endswith('.txt'):
         print(f"Warning: Output file does not have a .txt extension: {args.txt_file}")
         extract_msgids(args.po_file, args.txt_file)
    else:
        extract_msgids(args.po_file, args.txt_file)

# Example Usage:
# python extract_po_to_txt.py locale/zh_Hans/LC_MESSAGES/django.po translations_to_do.txt 