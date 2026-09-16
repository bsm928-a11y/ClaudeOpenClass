import hashlib
import html
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

DATA_FILE = Path(__file__).parent / "guestboard.json"


def load_entries() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_entries(entries: list[dict]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def render_entry(entry: dict) -> str:
    name = html.escape(entry["name"])
    message = html.escape(entry["message"]).replace("\n", "<br>")
    created_at = html.escape(entry["created_at"])
    return f"""
    <article class="entry">
        <header>
            <span class="entry-name">{name}</span>
            <span class="entry-date">{created_at}</span>
        </header>
        <p class="entry-message">{message}</p>
        <form class="delete-form" method="post" action="/delete">
            <input type="hidden" name="entry_id" value="{entry['id']}">
            <input type="password" name="password" placeholder="비밀번호" required>
            <button type="submit">삭제</button>
        </form>
    </article>
    """


def render_page(entries: list[dict], error: str = "") -> str:
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""

    if entries:
        entries_html = "".join(render_entry(e) for e in reversed(entries))
    else:
        entries_html = '<p class="empty">아직 작성된 글이 없습니다. 첫 방문자가 되어보세요!</p>'

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>방명록</title>
        <style>
            :root {{
                --green: #2e7d32;
                --green-dark: #1b5e20;
                --green-light: #e8f5e9;
                --green-accent: #66bb6a;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
                background: var(--green-light);
                margin: 0;
                padding: 0 16px 60px;
                color: #1a1a1a;
            }}
            .container {{ max-width: 640px; margin: 0 auto; }}
            .banner {{
                background: linear-gradient(135deg, var(--green), var(--green-dark));
                color: white;
                margin: 0 -16px;
                padding: 48px 16px 32px;
                text-align: center;
                border-radius: 0 0 24px 24px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
            }}
            .banner h1 {{ margin: 0 0 8px; font-size: 1.8rem; }}
            .banner p {{ margin: 0; opacity: 0.9; font-size: 0.95rem; }}

            .write-card {{
                background: white;
                border-radius: 16px;
                padding: 20px;
                margin-top: -24px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            }}
            .write-card h2 {{ margin: 0 0 12px; font-size: 1.1rem; color: var(--green-dark); }}
            .write-card form {{ display: flex; flex-direction: column; gap: 10px; }}
            .row {{ display: flex; gap: 10px; }}
            .row input {{ flex: 1; }}
            input, textarea {{
                border: 1px solid #d0e0d2;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 0.95rem;
                font-family: inherit;
                width: 100%;
            }}
            input:focus, textarea:focus {{
                outline: none;
                border-color: var(--green-accent);
            }}
            textarea {{ resize: vertical; min-height: 80px; }}
            .write-card button[type="submit"] {{
                background: var(--green);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
                transition: background 0.15s;
            }}
            .write-card button[type="submit"]:hover {{ background: var(--green-dark); }}

            .entries {{ margin-top: 24px; display: flex; flex-direction: column; gap: 14px; }}
            .entry {{
                background: white;
                border-radius: 14px;
                padding: 16px 18px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
                border-left: 4px solid var(--green-accent);
            }}
            .entry header {{
                display: flex;
                justify-content: space-between;
                align-items: baseline;
                margin-bottom: 8px;
            }}
            .entry-name {{ font-weight: bold; color: var(--green-dark); }}
            .entry-date {{ font-size: 0.8rem; color: #888; }}
            .entry-message {{
                margin: 0 0 10px;
                line-height: 1.5;
                white-space: pre-wrap;
                word-break: break-word;
            }}
            .delete-form {{ display: flex; gap: 6px; justify-content: flex-end; }}
            .delete-form input {{
                width: 110px;
                padding: 6px 8px;
                font-size: 0.8rem;
            }}
            .delete-form button {{
                background: none;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 0.8rem;
                color: #888;
                cursor: pointer;
            }}
            .delete-form button:hover {{ border-color: #d32f2f; color: #d32f2f; }}

            .empty {{ text-align: center; color: #888; margin-top: 40px; }}
            .error {{
                background: #ffebee;
                color: #c62828;
                border-radius: 8px;
                padding: 10px 14px;
                margin-top: 16px;
                font-size: 0.9rem;
                text-align: center;
            }}
            .count {{ text-align: center; color: var(--green-dark); font-size: 0.85rem; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="banner">
                <h1>🌿 방명록</h1>
                <p>다녀가신 흔적을 남겨주세요</p>
            </div>

            <div class="write-card">
                <h2>글 남기기</h2>
                <form method="post" action="/add">
                    <div class="row">
                        <input type="text" name="name" placeholder="이름" maxlength="30" required>
                        <input type="password" name="password" placeholder="비밀번호 (삭제 시 필요)" maxlength="50" required>
                    </div>
                    <textarea name="message" placeholder="방명록 내용을 남겨주세요" maxlength="500" required></textarea>
                    <button type="submit">남기기</button>
                </form>
            </div>

            {error_html}

            <p class="count">총 {len(entries)}개의 글</p>
            <div class="entries">
                {entries_html}
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def index():
    return render_page(load_entries())


@app.post("/add", response_class=HTMLResponse)
def add(request: Request, name: str = Form(...), message: str = Form(...), password: str = Form(...)):
    name = name.strip()
    message = message.strip()

    entries = load_entries()

    if name and message and password:
        entries.append(
            {
                "id": str(uuid.uuid4()),
                "name": name[:30],
                "message": message[:500],
                "password_hash": hash_password(password),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "ip": client_ip(request),
            }
        )
        save_entries(entries)

    return render_page(entries)


@app.post("/delete", response_class=HTMLResponse)
def delete(entry_id: str = Form(...), password: str = Form(...)):
    entries = load_entries()
    target = next((e for e in entries if e["id"] == entry_id), None)

    if target is None:
        return render_page(entries, error="이미 삭제된 글입니다.")

    if target["password_hash"] != hash_password(password):
        return render_page(entries, error="비밀번호가 일치하지 않습니다.")

    entries = [e for e in entries if e["id"] != entry_id]
    save_entries(entries)
    return render_page(entries)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
