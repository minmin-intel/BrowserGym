def filter_snapshot(snapshot_text:str):
    lines = snapshot_text.split("\n")
    retained_lines = []
    for line in lines:
        if ("cell" in line) or ("row" in line) or ("tab" in line):
            pass
        else:
            retained_lines.append(line)
    # join the lines back together
    filtered_axtree = "\n".join(retained_lines)
    # print(f"Filtered axtree:\n{filtered_axtree}")
    return filtered_axtree
    
