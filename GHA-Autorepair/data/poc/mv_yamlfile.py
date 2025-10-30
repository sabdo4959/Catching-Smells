import csv
import os
import shutil

csv_file = '/Users/nam/Desktop/repository/Catching-Smells/GHA-Autorepair/data/poc/poc_list.csv'
src_dir = '/Users/nam/workflows/'
dst_dir = '/Users/nam/Desktop/repository/Catching-Smells/GHA-Autorepair/data/poc/'

#dst_dir = '/Users/nam/workflows/'
#src_dir = '/Users/nam/Desktop/repository/Catching-Smells/GHA-Autorepair/data/poc/'

with open(csv_file, newline='') as f:
    reader = csv.reader(f)
    for row in reader:
        print(row)
        for yaml_file in row:
            yaml_file = yaml_file.strip()
            if not yaml_file:  # 빈 문자열 건너뜀
                continue
            src_path = os.path.join(src_dir, yaml_file)
            dst_path = os.path.join(dst_dir, yaml_file)
            if os.path.exists(src_path):
                shutil.copy(src_path, dst_path)
                print(f"Moved: {src_path} -> {dst_path}")
            else:
                print(f"File not found: {src_path}")