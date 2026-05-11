"""Automated health check for CSV stock data folders.

Usage: python3 health_check.py <folder_path> [--compare <other_folder>]
"""
import os
import sys
import csv
import argparse


def check_folder(folder_path):
    """Check a folder of CSV files for integrity and date ranges."""
    folder_path = os.path.expanduser(folder_path)
    if not os.path.isdir(folder_path):
        print(f"ERROR: {folder_path} is not a directory")
        sys.exit(1)

    files = sorted(f for f in os.listdir(folder_path) if f.endswith('.csv'))
    total = len(files)
    valid_files = []
    invalid_files = []
    min_date = '9999-12-31'
    max_date = '0000-01-01'
    total_rows = 0
    size_total = 0

    for f in files:
        path = os.path.join(folder_path, f)
        size_total += os.path.getsize(path)
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                rows = list(csv.reader(fh))
            if len(rows) < 2:
                invalid_files.append(f"{f}: too few rows ({len(rows)})")
                continue
            dates = []
            for r in rows[1:]:
                if r and len(r) >= 7:
                    d = r[0].strip().strip('"')
                    if d and d[4:5] == '-' and d[7:8] == '-':
                        dates.append(d)
            if not dates:
                invalid_files.append(f"{f}: no parseable dates ({len(rows)-1} rows)")
                continue
            d_min = min(dates)
            d_max = max(dates)
            if d_min < min_date:
                min_date = d_min
            if d_max > max_date:
                max_date = d_max
            valid_files.append((f, len(rows) - 1, size_total // 1024, (d_min, d_max)))
            total_rows += len(rows) - 1
        except Exception as e:
            invalid_files.append(f"{f}: {e}")

    invalid_rate = len(invalid_files) / total if total > 0 else 0

    print(f"\n{'='*70}")
    print(f"Folder: {folder_path}")
    print(f"{'='*70}")
    print(f"  Total files:       {total}")
    print(f"  Valid files:       {len(valid_files)} ({total - len(invalid_files)}/{total})")
    print(f"  Invalid files:     {len(invalid_files)} ({invalid_rate*100:.1f}%)")
    print(f"  Date range:        [{min_date} ~ {max_date}]")
    print(f"  Total data rows:   {total_rows}")
    print(f"  Total size:        {size_total // 1024 // 1024} MB")
    print(f"  Gate check:        {'PASS' if invalid_rate <= 0.05 else 'FAIL (> 5% corruption)'}")

    if invalid_files:
        print(f"\n  Invalid files:")
        for item in invalid_files[:20]:
            print(f"    - {item}")
        if len(invalid_files) > 20:
            print(f"    ... and {len(invalid_files) - 20} more")

    # Print top/bottom row counts for sanity
    if valid_files:
        valid_files.sort(key=lambda x: x[1])
        print(f"\n  Smallest (5):")
        for name, rows, _, (dmin, dmax) in valid_files[:5]:
            print(f"    {name}: {rows} rows [{dmin} ~ {dmax}]")
        print(f"\n  Largest (5):")
        for name, rows, _, (dmin, dmax) in valid_files[-5:]:
            print(f"    {name}: {rows} rows [{dmin} ~ {dmax}]")

    return {
        'total': total,
        'valid': len(valid_files),
        'invalid': len(invalid_files),
        'invalid_rate': invalid_rate,
        'min_date': min_date,
        'max_date': max_date,
        'total_rows': total_rows,
        'size_mb': size_total // 1024 // 1024,
    }


def compare_overlaps(folder_a, folder_b):
    """Check file name overlap between two folders."""
    a_names = set()
    b_names = set()
    for f in os.listdir(folder_a):
        if f.endswith('.csv'):
            base = f.rsplit('_', 1)[0]  # '1101.TW_台泥.csv' -> '1101.TW'
            a_names.add(base)
    for f in os.listdir(folder_b):
        if f.endswith('.csv'):
            base = f.rsplit('_', 1)[0]
            b_names.add(base)

    overlap = a_names & b_names
    only_a = a_names - b_names
    only_b = b_names - a_names

    print(f"\n{'='*70}")
    print(f"Overlap analysis")
    print(f"{'='*70}")
    print(f"  Files in A only:     {len(only_a)}")
    print(f"  Files in B only:     {len(only_b)}")
    print(f"  Files in BOTH:       {len(overlap)}")
    print(f"  Expected union:      {len(a_names | b_names)}")
    return overlap


def main():
    parser = argparse.ArgumentParser(description='CSV stock data health check')
    parser.add_argument('folder', help='Path to CSV folder')
    parser.add_argument('--compare', help='Second folder for overlap analysis', default=None)
    args = parser.parse_args()

    r1 = check_folder(args.folder)
    if args.compare:
        r2 = check_folder(args.compare)
        compare_overlaps(args.folder, args.compare)

    print()


if __name__ == "__main__":
    main()
