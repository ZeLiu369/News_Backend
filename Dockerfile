# 使用官方 Python 3.12 镜像
FROM python:3.12

# 设置工作目录
WORKDIR /app

# 安装 Poetry
RUN pip install poetry

# 复制 poetry 配置文件（如果有 lock 文件也一起复制更快）
COPY pyproject.toml poetry.lock ./

# 安装依赖（生产环境，不安装 dev 依赖）
RUN poetry install --no-root

# 复制你的项目代码
COPY . .

# 设置启动命令（兼容 Railway）
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
