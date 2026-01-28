import os
import re

FILES = [
    "_posts/2014/2014-02-25-writing-google-glass-apps-with-the-gdk-sneak-peek.md",
    "_posts/2014/2014-05-22-inspecting-and-debugging-api-versions-with-runscope.md",
    "_posts/2015-2020/2015-06-18-collecting-wedding-photos-with-twilio-mms.md",
    "_posts/2015-2020/2019-09-29-making-a-zwift-clone-part-4.md",
    "_posts/2015-2020/2019-03-17-making-a-zwift-clone-part-1.md",
    "_posts/2015-2020/2019-07-14-introducing-bark-mode.md",
    "_posts/2015-2020/2015-01-20-how-ghost-inspector-helped-me-furnish-my-house.md",
    "_posts/2015-2020/2016-09-06-strange-copy-pasta-in-developer-resumes.md",
    "_posts/2021-2025/2025-08-01-31-days-with-claude-code-what-i-learned.md",
    "_posts/2021-2025/2025-07-15-how-much-code-could-claude-code-code-if-claude-code-could-code-code-it-can.md"
]

def remove_slug(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        removed = False
        in_frontmatter = False
        dash_count = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == '---':
                dash_count += 1
            
            if dash_count < 2:
                # We are in front matter (or start of)
                if line.startswith('audio_slug:'):
                    removed = True
                    continue
            
            new_lines.append(line)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        if removed:
            print(f"Removed audio_slug from {filepath}")
        else:
            print(f"No audio_slug found in {filepath}")
            
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    for f in FILES:
        if os.path.exists(f):
            remove_slug(f)
        else:
            print(f"File not found: {f}")
