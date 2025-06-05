import re

def clean_log_text(log_text: str) -> str:
    """Remove timestamps and clean up the log text."""
    # Split into lines and remove timestamps
    lines = []
    for line in log_text.split('\n'):
        # Remove timestamp pattern [HH:MM:SS.mmm]
        if line.strip():
            # Find the first ']' after a timestamp
            if ']' in line:
                timestamp_end = line.find(']') + 1
                line = line[timestamp_end:].strip()
            lines.append(line)
    
    return '\n'.join(lines)

def extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown formatting."""
    text = text.strip()
    # Remove triple backticks and optional 'json'
    text = re.sub(r'^```json\s*|^```|```$', '', text, flags=re.MULTILINE).strip()
    # Extract the first {...} block if extra text is present
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        return match.group(0)
    return text 