import asyncio
import httpx
from fastapi import FastAPI
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# --- 1. 应用实例和内存缓存 ---

# 创建 FastAPI 应用实例
# 我们可以在这里加上标题、描述等元数据，会自动显示在文档里
app = FastAPI(
    title="Tech News Hot List API",
    description="An API that provides a dynamically ranked list of tech news events.",
    version="1.0.0",
)

# 内存缓存: 这个列表将作为我们的“数据库”，存储热榜的计算结果。
# 它是一个全局变量，在应用的整个生命周期中存在。
hot_list_cache: List[Dict[str, Any]] = []

# --- 2. 核心业务逻辑: 更新热榜 ---

# async 异步函数: 执行过程中 可以暂停, 并在稍后从暂停的地方继续执行。


async def update_hot_list():
    """
    从上游API获取新闻， 算法计算热度分，然后更新内存缓存。
    """
    print(f"[{datetime.now()}] Starting hot list update task...")

    # 使用 httpx 异步地请求上游 API
    try:
        # asynchronous HTTP client
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 建立网络连接。
            # 发送 HTTP 请求。
            # 接收原始的 HTTP 响应。
            # 将原始响应封装成 httpx.Response 对象
            response = await client.get('https://techsum-server.datasum.ai/api/events')
            # 如果请求失败 (比如404或500)，下一行会抛出异常
            response.raise_for_status()
            data = response.json()
            # if articles key is not found, return an empty list
            events = data.get("articles", [])
    except httpx.RequestError as e:
        print(f"Error: Failed to fetch data from upstream API. {e}")
        # 如果获取失败，就不继续执行，等待下一次任务
        return
    except Exception as e:
        print(f"An unexpected error occurred during fetch: {e}")
        return

    scored_events: List[Dict[str, Any]] = []  # 类型注解
    for event in events:
        try:
            # --- 我们的热度排名算法 ---
            P: float = float(event.get("importance", 0))

            # 解析时间字符串。这是一个简化处理，对于大多数标准格式有效。
            # "2025-06-18 09:00:00 Wed" -> "2025-06-18 09:00:00"
            date_str_part = " ".join(
                event.get("earliest_published", "").split(" ")[0:2])
            publish_date = datetime.strptime(
                date_str_part, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

            now_utc = datetime.now(timezone.utc)
            T: float = (now_utc - publish_date).total_seconds() / \
                3600.0  # 以小时为单位的“新闻年龄”
            G: float = 1.8  # 重力因子

            # 防止T为负数（如果数据源时间有误）
            if T < 0:
                T = 0

            score = P / ((T + 2) ** G)

            # 将计算结果和需要的数据存入一个字典
            scored_events.append({
                "title": event.get("group_title"),
                "summary": event.get("group_summary"),
                "published_at": event.get("earliest_published"),
                "score": score,
            })
# data sample:
#             scored_events.append({
#     "title": sample_event.get("group_title"),      # "Quantum Computing Breakthrough Unveiled"
#     "summary": sample_event.get("group_summary"),  # "Scientists announce a major leap forward..."
#     "published_at": sample_event.get("earliest_published"), # "2025-06-18 09:00:00 Wed"
#     "score": score,                                 # 0.003637
# })
        except (ValueError, TypeError, KeyError) as e:
            # 如果某条数据格式有问题，打印错误并跳过，保证任务的健壮性
            print(
                f"Warning: Skipping one event due to data parsing error. Details: {e}")
            continue

    # 按分数从高到低排序
    scored_events.sort(key=lambda x: x["score"], reverse=True)

    # 用排序后的结果更新全局缓存变量 (取前50名)
    global hot_list_cache
    hot_list_cache = scored_events[:50]

    if hot_list_cache:
        print(
            f"[{datetime.now()}] Hot list updated successfully. Top item: \"{hot_list_cache[0]['title']}\"")
    else:
        print(f"[{datetime.now()}] Hot list update finished, but the list is empty.")


# --- 3. 后台定时任务 ---

async def background_scheduler():
    """
    一个无限循环的调度器，它会在应用启动后一直在后台运行。每15分钟运行一次
    """
    print("Background scheduler started.")
    while True:
        try:
            await update_hot_list()
        except Exception as e:
            # 即使update_hot_list内部有try-except，这里再加一层以确保循环本身不会因意外而崩溃
            print(f"Critical error in background task loop: {e}")

        # 任务执行完后，“睡眠”15分钟
        await asyncio.sleep(15 * 60)

# 使用FastAPI的生命周期事件: 当应用启动完成时，启动我们的后台任务

# when fastapi is started, call this function (FastAPI 会自动call await)


@app.on_event("startup")
async def startup_background_task():
    print("Application startup complete. Launching background scheduler...")
    # 使用 asyncio.create_task 让这个任务在后台运行，而不会阻塞应用本身的启动
    asyncio.create_task(background_scheduler())
    # 我们也可以在这里立即执行一次，避免应用刚启动时列表为空
    # await update_hot_list()


# --- 4. 对外暴露的 API 端点 ---

@app.get("/api/hot-list", summary="Get the current hot list", tags=["Ranking"])
def get_hot_list_endpoint():
    """
    这个端点(endpoint)暴露给前端。
        它非常快，因为它只是从内存中直接读取`hot_list_cache`的结果，而不需要做任何计算。
        """
    return {
        "retrieved_at_utc": datetime.now(timezone.utc),
        "item_count": len(hot_list_cache),
        "data": hot_list_cache,
    }


@app.get("/", summary="Health Check", tags=["System"])
def health_check():
    """
    提供一个简单的健康检查端点，方便监控。
    """
    return {"status": "ok"}
