import os
import glob
import yaml
from datetime import datetime
import re
import markdown

IMAGE_MAX_WIDTH = "720px"
DOCS_DIR = "./docs"
POSTS_DIR = os.path.join(DOCS_DIR, "blog", "posts")
OUTPUT_FILE = os.path.join(DOCS_DIR, "blog.md")
AUTHORS_FILE = os.path.join(DOCS_DIR, "blog", ".authors.yml")
MORE_TAG = "<!-- more -->"

WORDS_PER_MINUTE = 200

def strip_front_matter(md_text):
    md_text = md_text.lstrip("\ufeff").lstrip()
    lines = md_text.splitlines()
    cleaned = []
    inside_yaml = False
    yaml_seen = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("---") and not yaml_seen:
            inside_yaml = True
            yaml_seen = True
            continue

        if stripped.startswith("---") and inside_yaml:
            inside_yaml = False
            continue

        if inside_yaml:
            continue

        if not cleaned and re.match(r"^[a-zA-Z0-9_-]+\s*:\s*.+$", stripped):
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()

def process_images(html):
    def repl(match):
        attrs = match.group(1)

        if(__debug__):
            attrs = re.sub(
                r'src=["\']img/',
                'src="posts/institucional/img/',
                attrs
           )
        else:
            attrs = re.sub(
                r'src=["\']img/',
                'src="institucional-zensical/posts/institucional/img/',
                attrs
            )

        attrs = re.sub(r'style=["\'][^"\']*["\']', '', attrs).strip()

        style = f"max-width:{IMAGE_MAX_WIDTH}; width:36%;"

        return f'<img {attrs} style="{style}">'

    return re.sub(r"<img\s+([^>]+)>", repl, html)

def extract_readtime(text):
    match = re.search(r"^\s*readtime\s*:\s*(\d+)", text, re.MULTILINE)
    return int(match.group(1)) if match else None

def calculate_readtime(text):
    words = re.findall(r"\w+", text)
    return max(1, round(len(words) / WORDS_PER_MINUTE))

def load_authors():
    try:
        with open(AUTHORS_FILE, "r", encoding="utf-8") as f:
            return (yaml.safe_load(f) or {}).get("authors", {})
    except FileNotFoundError:
        return {}

def parse_front_matter(content):
    if not content.startswith("---"):
        return {}, content
    _, fm, body = content.split("---", 2)
    return yaml.safe_load(fm) or {}, body.strip()

def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d de %B de %Y")
    except Exception:
        return date_str or "Data desconhecida"

def extract_author(metadata):
    if isinstance(metadata.get("author"), str):
        return metadata["author"]
    if isinstance(metadata.get("authors"), list):
        return metadata["authors"][0]
    return None

def extract_title(metadata, body):
    if metadata.get("title"):
        return metadata["title"]
    match = re.search(r"^\s*#\s+(.+)", body, re.MULTILINE)
    return match.group(1).strip() if match else "Título sem nome"

def render_markdown(md_text):
    html = markdown.markdown(
        md_text,
        extensions=[
            "extra",
            "admonition",
            "tables",
            "attr_list",
            "md_in_html",
            "toc"
        ],
        output_format="html5"
    )
    return process_images(html)

def get_category_from_path(file_path):
    rel = os.path.relpath(file_path, POSTS_DIR)
    parts = rel.split(os.sep)
    return parts[0].capitalize() if len(parts) > 1 else "Geral"

def generate_blog_page():
    authors_data = load_authors()

    post_files = glob.glob(os.path.join(POSTS_DIR, "**/*.md"), recursive=True)

    posts_by_category = {}

    for file_path in post_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        metadata, body = parse_front_matter(content)

        category = get_category_from_path(file_path)

        clean_body = strip_front_matter(strip_front_matter(body))
        clean_body = re.sub(
            r"^\s*readtime\s*:\s*\d+\s*$",
            "",
            clean_body,
            flags=re.MULTILINE
        )

        readtime = (
            metadata.get("readtime")
            or extract_readtime(content)
            or calculate_readtime(clean_body)
        )

        date = format_date(metadata.get("date"))

        author_key = extract_author(metadata)
        author_info = authors_data.get(author_key, {})
        author_name = author_info.get("name", "Autor Desconhecido")
        author_avatar = author_info.get("avatar", "https://via.placeholder.com/50")

        snippet_html = render_markdown(
            clean_body.split(MORE_TAG)[0].strip()
        )

        link_path = os.path.splitext(
            os.path.relpath(file_path, DOCS_DIR).replace("\\", "/")
        )[0]

        post_html = f"""
<div class="post-item" data-category="{category}">
  <div style="display:flex; gap:15px; margin-bottom:25px;">
    <img src="{author_avatar}"
         alt="{author_name}"
         style="border-radius:50%; width:50px; height:50px;">
    <div>
      <p style="margin:0; font-size:0.85em; color:#aaa;">
        {date} em <strong>{category}</strong> (leitura: {readtime} min)
      </p>
      {snippet_html}
      <a href="/{link_path}/" class="md-button md-button--primary">
        Continuar leitura
      </a>
    </div>
  </div>
</div>
<hr>
"""

        posts_by_category.setdefault(category, []).append(post_html)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        f.write("---\n"
                "icon: lucide/message-square-text\n"
                 "---\n")
        f.write("# Blog\n\n")

        for category, posts in sorted(posts_by_category.items()):
            f.write(f"## {category}\n\n")
            f.write("\n".join(posts))

        f.write("""
<script>
(function () {
  function filter(category) {
    document.querySelectorAll('.post-item').forEach(post => {
      post.style.display =
        !category || post.dataset.category === category ? '' : 'none';
    });
  }

  function setActive(link) {
    document.querySelectorAll('.md-nav__link').forEach(l =>
      l.classList.remove('md-nav__link--active')
    );
    link.classList.add('md-nav__link--active');
  }

  const hash = decodeURIComponent(location.hash.replace('#', ''));
  if (hash) filter(hash);

  document.querySelectorAll('.md-nav__link').forEach(link => {
    link.addEventListener('click', (e) => {
      const cat = link.textContent.trim();

      // evita o Zensical tentar decidir o ativo
      e.preventDefault();

      // atualiza filtro + hash
      filter(cat);
      location.hash = encodeURIComponent(cat);

      // força ativo correto
      setActive(link);
    });
  });
})();
</script>
""")

    print("GERADO HEHE;)")

if __name__ == "__main__":
    generate_blog_page()
