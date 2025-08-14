import pandas as pd
import re

# Log file content
with open("all_result_250806-01.log", encoding="utf-8") as f:
    log_content = f.read()

# Extract data
pattern = re.compile(r'Detecting smells for (.+)\nWe have found (\d+) smells((?:\n\t-.+)+)', re.MULTILINE)
matches = pattern.findall(log_content)

# Smell IDs and Descriptions (from provided data)
smell_ids = {str(i): f'Smell {i}' for i in range(1, 23)}

# Create dataframe structure
columns = ['Org', 'Repo', 'Yaml'] + [f'Smell {i}' for i in range(1, 23)]
data = []

for match in matches:
    yaml_path, smell_count, smells_block = match
    org, repo, yaml_file = re.match(r'\./\.github/workflows/(.+?)_(.+?)__(.+)', yaml_path).groups()
    smell_flags = {f'Smell {i}': '' for i in range(1, 23)}
    
    smells = re.findall(r'- (\d+)\.', smells_block)
    for smell in smells:
        smell_id = f'Smell {smell}'
        smell_flags[smell_id] = 'Tool'

    row = [org, repo, yaml_file] + [smell_flags[f'Smell {i}'] for i in range(1, 23)]
    data.append(row)

df = pd.DataFrame(data, columns=columns)

print(df)
df.to_csv("result_table.csv", index=False)
