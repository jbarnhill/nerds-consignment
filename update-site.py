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
            
        try:
            sort_issue = float(issue)
        except ValueError:
            match = re.search(r'\d+', issue)
            sort_issue = float(match.group()) if match else float('inf')
            
        return publisher, title, sort_issue, display_text
    return "Uncategorized", "Misc", float('inf'), name

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
        
        user_input = input("Push to remote repository? (y/n): ").strip().lower()
        if user_input in ['y', 'yes']:
            print("Pushing to remote repository...")
            subprocess.run(['git', 'push'], check=True)
            print("Git sync complete.")
        else:
            print("Git push skipped by user.")
    except subprocess.CalledProcessError as e:
        print(f"Error during git sync: {e}")
    except FileNotFoundError:
        print("Error: 'git' command not found. Please ensure git is installed and in your PATH.")

def check_and_process_images():
    """Checks if any images need processing and runs update-images.py if so."""
    needs_processing = False
    if os.path.exists(SOURCE_DIR):
        for filename in os.listdir(SOURCE_DIR):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')) and filename.count('-') < 2:
                needs_processing = True
                break
                
    if needs_processing:
        print("Unprocessed images found. Running update-images.py...")
        try:
            subprocess.run(['python', 'update-images.py'], check=True)
            print("Finished processing images.")
        except subprocess.CalledProcessError as e:
            print(f"Error running update-images.py: {e}")

def ensure_styles_and_scripts(soup):
    """Ensures the modern CSS makeover and tab logic exist in the HTML."""
    if not soup.head:
        head = soup.new_tag('head')
        soup.insert(0, head)
    
    # Remove old styles if they exist
    for old_style in soup.find_all('style', id=re.compile(r'tab-styles|main-styles|modern-styles')):
        old_style.decompose()

    if not soup.find('style', id='modern-styles'):
        style_tag = soup.new_tag('style', id='modern-styles')
        style_tag.string = """
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            :root {
                --bg-main: #F8FAFC; --bg-surface: #FFFFFF; --border-accent: #CBD5E1;
                --text-primary: #0F172A; --text-secondary: #475569; --accent-glow: #0284C7;
                --accent-alert: #DC2626;
            }
            body { background-color: var(--bg-main); color: var(--text-primary); font-family: 'Inter', sans-serif; line-height: 1.6; margin: 0; padding: 24px; }
            h1, h2, h3 { font-weight: 700; letter-spacing: -0.02em; color: var(--text-primary); margin-top: 0; }
            h1 { font-size: 2.25rem; margin-bottom: 8px; }
            h2 { font-size: 1.5rem; margin-bottom: 16px; border-bottom: 2px solid var(--border-accent); padding-bottom: 8px; }
            p, span { color: var(--text-secondary); font-size: 0.95rem; }
            a { color: var(--accent-glow); text-decoration: none; transition: color 0.2s ease; }
            a:hover { color: #0369A1; }
            .container { max-width: 1100px; margin: 0 auto; background-color: var(--bg-surface); border: 1px solid var(--border-accent); border-radius: 12px; padding: 24px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2); }
            ul { list-style: none; padding-left: 0; margin: 0; }
            li { background-color: #F1F5F9; border: 1px solid var(--border-accent); border-radius: 8px; padding: 16px; margin-bottom: 12px; transition: transform 0.2s ease, background-color 0.2s ease; }
            li:hover { transform: scale(1.01); background-color: #E2E8F0; border-color: var(--accent-glow); }
            .tab-nav { overflow: hidden; margin-bottom: 24px; display: flex; flex-wrap: wrap; gap: 8px; border-bottom: 1px solid var(--border-accent); padding-bottom: 16px; }
            .tab-nav button { background-color: #F1F5F9; color: var(--text-secondary); border: 1px solid var(--border-accent); cursor: pointer; padding: 10px 20px; transition: 0.3s; border-radius: 8px; font-weight: 500; }
            .tab-nav button:hover { background-color: var(--border-accent); color: var(--text-primary); }
            .tab-nav button.active { background-color: var(--accent-glow); color: var(--bg-main); border-color: var(--accent-glow); font-weight: 700; }
            .tab-panel { animation: fadeEffect 0.5s; display: none; }
            @keyframes fadeEffect { from {opacity: 0;} to {opacity: 1;} }
            header { text-align: center; margin-bottom: 40px; }
            footer { text-align: center; margin-top: 60px; padding: 20px; border-top: 1px solid var(--border-accent); }
        """
        soup.head.append(style_tag)
        
    if not soup.find('script', id='tab-logic'):
        script_tag = soup.new_tag('script', id='tab-logic')
        script_tag.string = """
            function openPublisher(evt, pubName) {
                var i, tabcontent, tablinks;
                tabcontent = document.getElementsByClassName("tab-panel");
                for (i = 0; i < tabcontent.length; i++) { 
                    tabcontent[i].style.display = "none"; 
                }
                tablinks = document.getElementsByClassName("tab-link");
                for (i = 0; i < tablinks.length; i++) { 
                    tablinks[i].className = tablinks[i].className.replace(" active", ""); 
                }
                document.getElementById(pubName).style.display = "block";
                evt.currentTarget.className += " active";
            }
        """
        soup.head.append(script_tag)

def ensure_page_counter(soup):
    """Ensures a page counter exists in the footer."""
    footer = soup.find('footer')
    if footer:
        counter_img = footer.find('img', id='page-counter')
        if not counter_img:
            counter_img = soup.new_tag('img', id='page-counter')
            counter_img['src'] = 'https://profile-counter.glitch.me/nerds_consignment_index/count.svg'
            counter_img['alt'] = 'Visitor Count'
            counter_img['style'] = 'margin-top: 15px; display: block; margin-left: auto; margin-right: auto;'
            footer.append(counter_img)

def main():
    check_and_process_images()


    if not os.path.exists(INDEX_FILE):
        print(f"Error: {INDEX_FILE} not found.")
        return

    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    if soup.title:
        soup.title.string = "Comic Auction Preview"

    header_h1 = soup.find('h1')
    if header_h1:
        header_h1.string = "Comic Auction Preview"

    for a_tag in soup.find_all('a'):
        if a_tag.get('href', '').startswith('mailto:'):
            a_tag['href'] = 'mailto:justindbarnhill@gmail.com,nerdyfeathers@gmail.com'
            a_tag.string = 'justindbarnhill@gmail.com or nerdyfeathers@gmail.com'

    ensure_styles_and_scripts(soup)
    ensure_page_counter(soup)

    content_div = soup.find('div', class_='content')
    if not content_div:
        print("No content div found.")
        return

    content_div.clear()

    items = []
    for filename in os.listdir(SOURCE_DIR):
        if filename in ['.DS_Store', 'Thumbs.db'] or filename.endswith('.tmp'):
            continue
        
        publisher, title, sort_issue, display_text = parse_filename(filename)
        items.append({
            'filename': filename,
            'publisher': publisher,
            'title': title,
            'sort_issue': sort_issue,
            'display': display_text
        })
    
    # Sort items
    items.sort(key=lambda x: (x['publisher'], x['title'], x['sort_issue'], x['display']))

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

    # Create Tab Navigation and Container
    tab_nav = soup.new_tag('div', attrs={'class': 'tab-nav'})
    tab_container = soup.new_tag('div', attrs={'class': 'tab-container'})
    content_div.append(tab_nav)
    content_div.append(tab_container)

    for i, (pub, titles) in enumerate(grouped.items()):
        pub_id = re.sub(r'[^a-zA-Z0-9]', '_', pub)
        
        # Create Tab Link
        btn = soup.new_tag('button', attrs={
            'class': 'tab-link' + (' active' if i == 0 else ''),
            'onclick': f"openPublisher(event, '{pub_id}')"
        })
        btn.string = pub
        tab_nav.append(btn)
        
        # Create Tab Panel
        panel = soup.new_tag('div', attrs={
            'id': pub_id,
            'class': 'tab-panel',
            'style': 'display: block;' if i == 0 else ''
        })
        tab_container.append(panel)

        for tit, file_items in titles.items():
            h3 = soup.new_tag('h3')
            h3.string = tit
            panel.append(h3)

            ul = soup.new_tag('ul')
            for item in file_items:
                li = soup.new_tag('li')
                a = soup.new_tag('a', href=f"{SOURCE_DIR}/{item['filename']}")
                a.string = item['display']
                li.append(a)
                ul.append(li)
            panel.append(ul)

    # Save changes
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    
    print("Local updates finished.")
    
    # Final Step: Git Sync
    sync_to_git()

if __name__ == "__main__":
    main()
