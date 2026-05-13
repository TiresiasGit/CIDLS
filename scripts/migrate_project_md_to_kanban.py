from html import escape
from pathlib import Path


START = "<!-- PROJECT_MD_MIGRATION_START -->"
END = "<!-- PROJECT_MD_MIGRATION_END -->"


def build_section(project_text):
    escaped = escape(project_text)
    return f"""
  {START}
  <section class="panel" id="project-md-archive">
    <h2 class="section-title">project.md廃止済みアーカイブ</h2>
    <p class="section-subtitle">project.mdは廃止済み。旧project.mdの全内容はkanban_project.htmlへ吸収し、以後のSoTはkanban_project.htmlとproject_kanban.html互換ミラーへ統一する。</p>
    <div class="trace">
      <strong>廃止ルール</strong>
      <span>project.mdを再作成しない。ナレッジ蓄積、タスク状態、Latest Run、CAPDkA Snapshotはkanban_project.htmlへ集約する。</span>
    </div>
    <pre style="white-space:pre-wrap; overflow:auto; max-height:560px; background:#fff; border:1px solid rgba(217,209,196,.95); border-radius:18px; padding:16px; line-height:1.55;">{escaped}</pre>
  </section>
  {END}
"""


def replace_section(html, section):
    if START in html and END in html:
        before = html[: html.index(START)]
        after = html[html.index(END) + len(END) :]
        return before.rstrip() + "\n" + section.strip("\n") + "\n" + after.lstrip()
    if "</main>" not in html:
        raise ValueError("kanban HTML does not contain </main>")
    return html.replace("</main>", section + "</main>", 1)


def main():
    root = Path(__file__).resolve().parents[1]
    project = root / "project.md"
    kanban = root / "kanban_project.html"
    mirror = root / "project_kanban.html"

    if project.exists():
        project_text = project.read_text(encoding="utf-8")
    else:
        base_html = kanban.read_text(encoding="utf-8")
        if START in base_html and END in base_html:
            mirror.write_text(base_html, encoding="utf-8", newline="\n")
            print("project.md already migrated")
            return 0
        raise FileNotFoundError("project.md is missing and no migrated archive exists")

    section = build_section(project_text)
    html = kanban.read_text(encoding="utf-8")
    updated = replace_section(html, section)
    kanban.write_text(updated, encoding="utf-8", newline="\n")
    mirror.write_text(updated, encoding="utf-8", newline="\n")
    print(kanban)
    print(mirror)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
