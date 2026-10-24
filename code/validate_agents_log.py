import re

def validate_log(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sections = content.strip().split("## [")
    if not sections or not sections[0].strip() == "":
        # First entry
        pass
    
    entries = ["## [" + s for s in sections if s.strip()]
    print(f"Total entries found: {len(entries)}")
    
    errors = []
    
    # 1. First entry must be SESSION START
    first = entries[0]
    if "SESSION START" not in first:
        errors.append("First entry is not SESSION START")
    else:
        req_start = ["tool=", "model=", "Repo Root:", "Branch:", "Worktree:", "Parent Agent:", "Language:", "Time Remaining:"]
        for r in req_start:
            if r not in first:
                errors.append(f"SESSION START missing: {r}")
                
    # 2. Subsequent entries must be per-turn
    for idx, e in enumerate(entries[1:], 1):
        lines = e.strip().split("\n")
        header = lines[0]
        # Check title
        if not re.match(r"^## \[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\] .+$", header):
            errors.append(f"Entry {idx} header invalid: {header}")
            
        req_turn = [
            "User Prompt (verbatim, secrets redacted):",
            "Agent Response Summary:",
            "Actions:",
            "Context:",
            "tool=",
            "model=",
            "branch=",
            "repo_root=",
            "worktree=",
            "parent_agent="
        ]
        for r in req_turn:
            if r not in e:
                errors.append(f"Entry {idx} ('{header[:30]}...') missing: '{r}'")
                
    if errors:
        print(f"FAILED validation with {len(errors)} errors:")
        for err in errors[:10]:
            print("  -", err)
        return False
    else:
        print("ALL VALIDATION CHECKS PASSED PERFECTLY!")
        return True

if __name__ == "__main__":
    import sys
    validate_log("log.txt")
