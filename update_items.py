import os
import re
import subprocess
from bs4 import BeautifulSoup

# Configuration
SOURCE_DIR = 'albany_silver'
INDEX_FILE = 'index.html'

def parse_filename(filename):
    # Expecting: Publisher - Title - Issue - Date.ext
    name, ext = os.path.splitext(filename)
    parts = [p.strip() for p in name.split('-')]
    if len(parts) >= 3:
        publisher = parts[0]
        title = parts[1]
        issue = parts[2]
        date = parts[3] if len(parts) > 3 else ''
        display_text = f"Issue {issue}"
        if date:
            display_text += f" - {date}"
        return publisher, title, display_text
    return "Uncategorized", "Misc", name

def sync_to_git():
    """Stages, commits, and pushes changes to git."""
    try:
        status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
        if not status:
            print("No changes detected. Skipping git sync.")
            return

        print("\nChanges detected. Syncing to git...")
        subprocess.run(['git', 'add', '-A'], check=True)
        subprocess.run(['git', 'commit', '-m', "Auto-update: Organized items"], check=True)
        print("Pushing to remote repository...")
        subprocess.run(['git', 'push'], check=True)
        print("Git sync complete.")
    except subprocess.CalledProcessError as e:
        print(f"Error during git sync: {e}")
    except FileNotFoundError:
        print("Error: 'git' command not found. Please ensure git is installed and in your PATH.")

def main():
    if not os.path.exists(INDEX_FILE):
        print(f"Error: {INDEX_FILE} not found.")
        return

    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    content_div = soup.find('div', class_='content')
    if not content_div:
        print("No content div found.")
        return

    # Clear current content completely to rebuild
    content_div.clear()
    
    # Add title back
    h1 = soup.new_tag('h1')
    h1.string = "Albany Silver"
    content_div.append(h1)

    items = []
    for filename in os.listdir(SOURCE_DIR):
        if filename in ['.DS_Store', 'Thumbs.db'] or filename.endswith('.tmp'):
            continue
        
        publisher, title, display_text = parse_filename(filename)
        items.append({
            'filename': filename,
            'publisher': publisher,
            'title': title,
            'display': display_text
        })
    
    # Sort items
    items.sort(key=lambda x: (x['publisher'], x['title'], x['display']))

    # Group by publisher -> title
    grouped = {}
    for item in items:
        pub = item['publisher']
        tit = item['title']
        if pub not in grouped:
            grouped[pub] = {}
        if tit not in grouped[pub]:
            grouped[pub][tit] = []
        grouped[pub][tit].append(item)

    for pub, titles in grouped.items():
        h2 = soup.new_tag('h2')
        h2.string = pub
        content_div.append(h2)

        for tit, file_items in titles.items():
            h3 = soup.new_tag('h3')
            h3.string = tit
            content_div.append(h3)

            ul = soup.new_tag('ul')
            for item in file_items:
                li = soup.new_tag('li')
                a = soup.new_tag('a', href=f"{SOURCE_DIR}/{item['filename']}")
                a.string = item['display']
                li.append(a)
                ul.append(li)
            content_div.append(ul)

    # Save changes
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    
    print("Local updates finished.")
    
    # Final Step: Git Sync
    sync_to_git()

if __name__ == "__main__":
    main()
