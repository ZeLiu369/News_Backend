# ==============================================================================
# 阶段一: 构建器 (Builder)
# 使用一个全功能的镜像来安装所有依赖
# ==============================================================================
FROM python:3.12 AS builder

# 设置 Poetry 版本和路径，让构建更稳定
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VERSION=1.8.2
ENV PATH="$POETRY_HOME/bin:$PATH"

# 安装 Poetry
RUN curl -sSL https://install.python-poetry.org | python -

# 创建一个非 root 用户，并设置工作目录
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app

# 复制项目依赖配置文件
COPY pyproject.toml poetry.lock ./

# 安装项目依赖到一个项目内的虚拟环境中
# --no-interaction and --no-ansi 是在CI/CD环境中推荐的选项
# poetry config virtualenvs.in-project true 会在项目目录下创建 .venv 文件夹
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-root --no-interaction --no-ansi


# 复制你的应用源代码
COPY . .


# ==============================================================================
# 阶段二: 最终运行环境 (Final Stage)
# 使用一个非常小巧的 slim 镜像来减小最终体积
# =================================p=============================================
FROM python:3.12-slim AS final

# 创建一个非 root 用户（和 builder 阶段保持一致）
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app
USER appuser

# 【关键步骤】从 builder 階段拷贝我们构建好的虚拟环境和应用代码
# 这样最终镜像就不再需要 Poetry 工具本身了
COPY --from=builder /home/appuser/app/.venv ./.venv
COPY --from=builder /home/appuser/app/ .

# 设置 PATH，让 shell 能找到虚拟环境里的可执行文件
ENV PATH="/home/appuser/app/.venv/bin:$PATH"

# 设置启动命令
# 我们现在可以直接调用虚拟环境里的 uvicorn，而不再需要 `poetry run`
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]