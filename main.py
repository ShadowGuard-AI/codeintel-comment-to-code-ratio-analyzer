#!/usr/bin/env python3

import argparse
import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def setup_argparse():
    """
    Sets up the argument parser for the command line interface.
    """
    parser = argparse.ArgumentParser(
        description="Calculates the ratio of comments to code lines in a project or file."
    )
    parser.add_argument(
        "path",
        help="Path to the file or directory to analyze.",
        type=str
    )
    parser.add_argument(
        "-e", "--exclude",
        help="Comma-separated list of file extensions to exclude (e.g., .txt,.log).",
        type=str,
        default=""
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Enable verbose output (debug logging).",
        action="store_true"
    )

    return parser.parse_args()


def calculate_comment_code_ratio(file_path, exclude_patterns=None):
    """
    Calculates the ratio of comments to code lines in a single file.
    Args:
        file_path (str): Path to the file to analyze.
        exclude_patterns (list): list of regex patterns for exclusion

    Returns:
        tuple: A tuple containing the comment count, code line count, and ratio.
               Returns (None, None, None) on error.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:  # Explicit encoding
            lines = f.readlines()
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None, None, None
    except PermissionError:
        logging.error(f"Permission denied: {file_path}")
        return None, None, None
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return None, None, None

    comment_count = 0
    code_line_count = 0
    # The delimiter that closes the block being read, or None outside
    # one. Tracking the delimiter, not just a flag, is what lets a
    # block that opens and closes on one line (a one line docstring,
    # a short C comment) count as one comment line without swallowing
    # the rest of the file, which the old toggle flag did: every line
    # after a one line docstring was counted as a comment.
    multiline_end = None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if multiline_end is not None:
            comment_count += 1
            if multiline_end in line:
                multiline_end = None
            continue

        if line.startswith("'''") or line.startswith('"""'):
            comment_count += 1
            delimiter = line[:3]
            if delimiter not in line[3:]:
                multiline_end = delimiter
            continue

        if line.startswith("/*"):
            comment_count += 1
            if "*/" not in line[2:]:
                multiline_end = "*/"
            continue

        if line.startswith('#') or line.startswith('//'):
            comment_count += 1
        else:
            code_line_count += 1

    if code_line_count > 0:
        ratio = comment_count / code_line_count
    else:
        ratio = 0.0  # Avoid division by zero

    return comment_count, code_line_count, ratio


def analyze_directory(directory_path, exclude_extensions=None):
    """
    Analyzes all files in a directory, calculates comment-to-code ratio for each,
    and prints a summary.
    Args:
        directory_path (str): Path to the directory to analyze.
        exclude_extensions (list): list of file extensions to exclude

    Returns:
        bool: True if files were analyzed or none failed, False if the
              run analyzed zero files because every file failed to read.
    """
    total_comment_lines = 0
    total_code_lines = 0
    file_count = 0
    skipped_count = 0

    if not os.path.isdir(directory_path):
        logging.error(f"Invalid directory path: {directory_path}")
        return False

    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)

            # Check if the file should be excluded based on extension
            if exclude_extensions:
                _, file_extension = os.path.splitext(file_path)
                if file_extension in exclude_extensions:
                    logging.debug(f"Skipping file (excluded extension): {file_path}")
                    continue

            # Validate that it is a file and skip if not
            if not os.path.isfile(file_path):
                logging.debug(f"Skipping non-file item: {file_path}")
                continue

            comment_count, code_line_count, ratio = calculate_comment_code_ratio(file_path)

            if comment_count is not None and code_line_count is not None:
                file_count += 1
                total_comment_lines += comment_count
                total_code_lines += code_line_count
                logging.info(f"File: {file_path}, Comment Lines: {comment_count}, Code Lines: {code_line_count}, Ratio: {ratio:.2f}")
            else:
                skipped_count += 1
                logging.warning(f"Skipping {file_path} due to error during analysis.")

    if total_code_lines > 0:
        total_ratio = total_comment_lines / total_code_lines
    else:
        total_ratio = 0.0

    print("\n--- Summary ---")
    print(f"Total Files Analyzed: {file_count}")
    if skipped_count:
        print(f"Total Files Skipped: {skipped_count}")
    print(f"Total Comment Lines: {total_comment_lines}")
    print(f"Total Code Lines: {total_code_lines}")
    print(f"Overall Comment-to-Code Ratio: {total_ratio:.2f}")

    return not (file_count == 0 and skipped_count > 0)


def main():
    """
    Main function to execute the comment-to-code ratio analyzer.
    """
    args = setup_argparse()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    path = args.path
    exclude_extensions_str = args.exclude
    exclude_extensions = [ext.strip() for ext in exclude_extensions_str.split(',') if ext.strip()] if exclude_extensions_str else None

    if os.path.isfile(path):
        comment_count, code_line_count, ratio = calculate_comment_code_ratio(path)
        if comment_count is not None and code_line_count is not None:
            print(f"File: {path}, Comment Lines: {comment_count}, Code Lines: {code_line_count}, Ratio: {ratio:.2f}")
        else:
            sys.exit(1)  # Exit with an error code
    elif os.path.isdir(path):
        if not analyze_directory(path, exclude_extensions):
            sys.exit(1)  # Every file in the directory failed to read
    else:
        logging.error(f"Invalid path: {path}")
        sys.exit(1)  # Exit with an error code

# Example Usage (For documentation purposes only)
# To actually execute, save as a .py file and run from the command line.
if __name__ == "__main__":
    # Example 1: Analyze a single file: python main.py my_file.py
    # Example 2: Analyze a directory: python main.py my_project_directory
    # Example 3: Analyze a directory, excluding .txt and .log files: python main.py my_project_directory -e .txt,.log
    # Example 4: Enable verbose output: python main.py my_project_directory -v
    main()