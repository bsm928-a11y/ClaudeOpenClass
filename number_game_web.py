import random
import uuid

from fastapi import Cookie, FastAPI, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

games: dict[str, dict] = {}


def new_game() -> dict:
    return {"answer": random.randint(1, 100), "attempts": 0, "message": "", "won": False}


def render_page(session_id: str, state: dict) -> str:
    if state["won"]:
        body = f"""
        <p class="result win">정답입니다! {state['attempts']}번 만에 맞추셨습니다. 축하합니다!</p>
        <a class="button" href="/new?session_id={session_id}">다시 하기</a>
        """
    else:
        body = f"""
        <p class="result">{state['message']}</p>
        <form method="post" action="/guess">
            <input type="hidden" name="session_id" value="{session_id}">
            <input type="number" name="guess" min="1" max="100" autofocus required>
            <button type="submit">확인</button>
        </form>
        <p class="attempts">시도 횟수: {state['attempts']}</p>
        """

    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <title>숫자 맞추기 게임</title>
        <style>
            body {{ font-family: sans-serif; max-width: 400px; margin: 60px auto; text-align: center; }}
            input {{ font-size: 1.2rem; padding: 6px; width: 100px; text-align: center; }}
            button, .button {{ font-size: 1.2rem; padding: 6px 14px; margin-left: 6px; cursor: pointer; text-decoration: none; }}
            .result {{ font-size: 1.1rem; min-height: 1.5em; }}
            .win {{ color: green; font-weight: bold; }}
            .attempts {{ color: #666; }}
        </style>
    </head>
    <body>
        <h1>1~100 숫자 맞추기</h1>
        {body}
    </body>
    </html>
    """


def get_state(session_id: str | None) -> tuple[str, dict]:
    if session_id is None or session_id not in games:
        session_id = str(uuid.uuid4())
        games[session_id] = new_game()
    return session_id, games[session_id]


@app.get("/", response_class=HTMLResponse)
def index(response: Response, session_id: str | None = Cookie(default=None)):
    session_id, state = get_state(session_id)
    response.set_cookie("session_id", session_id)
    return render_page(session_id, state)


@app.post("/guess", response_class=HTMLResponse)
def guess(
    response: Response,
    guess: int = Form(...),
    session_id: str | None = Form(default=None),
    cookie_session_id: str | None = Cookie(default=None, alias="session_id"),
):
    # 폼에 담겨온 session_id를 우선 신뢰한다: 쿠키가 저장되지 않는 환경(내장 브라우저 등)에서도
    # 같은 페이지에서 이어서 추측하면 세션이 끊기지 않도록 하기 위함.
    session_id, state = get_state(session_id or cookie_session_id)
    response.set_cookie("session_id", session_id)

    if not state["won"]:
        state["attempts"] += 1
        if guess < state["answer"]:
            state["message"] = "낮습니다."
        elif guess > state["answer"]:
            state["message"] = "높습니다."
        else:
            state["won"] = True

    return render_page(session_id, state)


@app.get("/new")
def new(session_id: str | None = None, cookie_session_id: str | None = Cookie(default=None, alias="session_id")):
    target = session_id or cookie_session_id
    if target is not None:
        games[target] = new_game()
    return RedirectResponse(url="/")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
