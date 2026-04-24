from __future__ import annotations

import html


def markdown_to_wechat_html(markdown_text: str) -> str:
    # MVP: lightweight conversion to keep WeChat-compatible inline styles.
    lines = markdown_text.splitlines()
    output = ["<article style='font-size:16px;line-height:1.8;color:#222;'>"]
    for line in lines:
        escaped = html.escape(line.strip())
        if not escaped:
            output.append("<p style='margin:12px 0;'></p>")
        elif escaped.startswith("# "):
            output.append(f"<h1 style='font-size:24px;margin:18px 0 12px;'>{escaped[2:]}</h1>")
        elif escaped.startswith("## "):
            output.append(
                f"<h2 style='font-size:20px;margin:16px 0 10px;color:#0b57d0;'>{escaped[3:]}</h2>"
            )
        elif escaped.startswith("&gt; "):
            output.append(
                f"<blockquote style='border-left:4px solid #ddd;padding-left:10px;color:#555;'>{escaped[5:]}</blockquote>"
            )
        elif escaped.startswith("---"):
            output.append("<hr style='border:none;border-top:1px solid #eee;margin:20px 0;' />")
        else:
            escaped = escaped.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
            output.append(f"<p style='margin:12px 0;'>{escaped}</p>")

    output.append("</article>")
    return "\n".join(output)
