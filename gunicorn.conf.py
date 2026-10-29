# gunicorn.conf.py 示例
import multiprocessing

# 监听地址和端口（比如本地的 8000 端口）
bind = "127.0.0.1:8000"  # 这样只能通过本地访问，外网不可以访问，外网访问可以通过nginx

# 开启的进程数 (Worker 数量)
# 一般公式是：(2 x CPU核心数) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# 每个进程开启的线程数
threads = 1

# 工作模式（通常用 sync 或 gevent，如果是 FastAPI 推荐用 uvicorn.workers.UvicornWorker）
worker_class = "uvicorn.workers.UvicornWorker"

# ---- 超时设置 ------
# 请求超时的时间，长任务需要调大 超过这个时间没响应 Gunicorn 会杀掉并重启 worker
timeout = 30

# 当 Gunicorn 收到“重启”或“停止”指令时，它会给正在处理请求的 Worker（工作进程）最多 30 秒的时间，让它们把手头的事情干完再退出。
graceful_timeout = 30

# “如果一个客户端发完请求后，5 秒钟之内没有发新的请求，你就主动把这个连接关掉，把资源释放出来。”
keepalive = 5

# 守护进程（是否在后台运行）
daemon = False

# --- 日志配置 ---
# 日志配置（注意：这里配置的是 Gunicorn 自身的访问日志和错误日志，不是你代码里的业务日志）
# 访问日志路径，'-' 表示输出到 stdout
accesslog = "/home/hrsystem/hr-backend/log/accesslog.log"

# 错误日志路径，'-' 表示输出到 stderr
errorlog = "/home/hrsystem/hr-backend/log/errorlog.log"

# 日志级别: debug, info, warning, error, critical
loglevel = "info"


# --- 性能与安全 ---
# 限制请求行大小 (防止 HTTP 攻击)
limit_request_line = 4094

# 限制请求头字段数量
limit_request_fields = 100

# 限制请求头字段大小
limit_request_field_size = 8190

# --- 进程管理 ---
# 是否在 master 进程中预加载应用 (节省内存，但需注意数据库连接 fork 问题)
preload_app = False


# --- 钩子函数 (可选) ---
def on_starting(server):
    print("Gunicorn is starting...")


def on_reload(server):
    print("Gunicorn is reloading...")


def worker_int(worker):
    print(f"Worker {worker.pid} received INT signal")
