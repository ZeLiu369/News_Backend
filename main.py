from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello Docker + FastAPI + Poetry"}

# the same as
# def read_root():
#     return {"message": "Hello, World!"}
# read_root = app.get("/")(read_root)
# 这是 FastAPI 框架提供的一个路由装饰器。
# 它的意思是：当客户端通过 HTTP GET 请求访问 / 路径时（也就是网站根目录），就会执行下面定义的 read_root() 函数。
# “当有人访问这个路径时，请自动调用我下面这个函数去处理。”
