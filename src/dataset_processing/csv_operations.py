
import csv
import sys
from pathlib import Path

def split_csv(input_file, output_prefix=None):
    """
    Split a CSV file into two halves.
    
    Args:
        input_file: Path to the input CSV file
        output_prefix: Prefix for output files (default: input filename without extension)
    
    Returns:
        Tuple of (first_half_path, second_half_path)
    """
    input_path = Path(input_file)
    
    if output_prefix is None:
        output_prefix = input_path.stem
    
    output_dir = input_path.parent
    first_half = output_dir / f"{output_prefix}_part1.csv"
    second_half = output_dir / f"{output_prefix}_part2.csv"
    
    # Read all rows
    with open(input_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    
    # Calculate split point
    total_rows = len(rows)
    split_point = total_rows // 2
    
    # Write first half
    with open(first_half, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows[:split_point])
    
    # Write second half
    with open(second_half, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows[split_point:])
    
    print(f"Split complete:")
    print(f"  First half ({split_point} rows): {first_half}")
    print(f"  Second half ({total_rows - split_point} rows): {second_half}")
    
    return str(first_half), str(second_half)


def merge_csv(file1, file2, output_file, skip_header_second=True):
    """
    Merge two CSV files into one.
    
    Args:
        file1: Path to first CSV file
        file2: Path to second CSV file
        output_file: Path for the merged output file
        skip_header_second: If True, skip header row from second file (default: True)
    
    Returns:
        Path to merged file
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        
        # Write first file completely
        with open(file1, 'r', newline='', encoding='utf-8') as f1:
            reader = csv.reader(f1)
            for row in reader:
                writer.writerow(row)
        
        # Write second file (optionally skipping header)
        with open(file2, 'r', newline='', encoding='utf-8') as f2:
            reader = csv.reader(f2)
            if skip_header_second:
                next(reader)  # Skip header
            for row in reader:
                writer.writerow(row)
    
    print(f"Merged {file1} and {file2} into {output_file}")
    return output_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Split: python csv_operations.py split <input.csv> [output_prefix]")
        print("  Merge: python csv_operations.py merge <file1.csv> <file2.csv> <output.csv>")
        sys.exit(1)
    
    operation = sys.argv[1].lower()
    
    if operation == "split":
        if len(sys.argv) < 3:
            print("Error: Input file required")
            sys.exit(1)
        input_file = sys.argv[2]
        output_prefix = sys.argv[3] if len(sys.argv) > 3 else None
        split_csv(input_file, output_prefix)
    
    elif operation == "merge":
        if len(sys.argv) < 5:
            print("Error: Two input files and output file required")
            sys.exit(1)
        file1 = sys.argv[2]
        file2 = sys.argv[3]
        output_file = sys.argv[4]
        merge_csv(file1, file2, output_file)
    
    else:
        print(f"Error: Unknown operation '{operation}'")
        print("Valid operations: split, merge")
        sys.exit(1)
