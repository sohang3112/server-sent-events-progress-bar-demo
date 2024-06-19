import asyncio
import json
import random
import re
import logging

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse


app = FastAPI()

next_session_id = 0
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
def index(request: Request):
    global next_session_id
    session_id = next_session_id
    next_session_id += 1
    return templates.TemplateResponse(
        request=request, name="index.html", context={"id": session_id}
    )


def server_sent_event(data: str, **kwargs: str):
    ans = re.sub("^", "data: ", data, flags=re.MULTILINE)
    if kwargs:
        ans += "\n" + "\n".join([f"{key}: {value}" for key, value in kwargs.items()])
    return ans + "\n\n"


async def progress_bar(session_id: int):
    for progress in range(100):
        data = {"progress": progress}
        print("Id:", session_id, "Progress:", progress, flush=True)
        yield server_sent_event(json.dumps(data), event="progress", id=session_id)
        milliseconds = random.randint(
            100, 2000
        )  # random timeout b/w 0.1 secs to 2 secs
        await asyncio.sleep(milliseconds / 1000)


# TODO: discard SSE session when client closes connection early
@app.get("/progress")
async def progress_bar_sse(session_id: int):
    return StreamingResponse(progress_bar(session_id), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    try:
        uvicorn.run(app, port=8000)
    except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
        print("Bye!")

    # TODO: replace with hypercorn for HTTP/2 support -
    #    but problem is it's not displaying logs of failed network requests
    # we want HTTP/2 support, so use hypercorn ASGI server instead of uvicorn
    # from hypercorn.config import Config
    # from hypercorn.asyncio import serve
    # asyncio.run(serve(app, Config()))
