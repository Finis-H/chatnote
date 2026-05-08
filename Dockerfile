# 1. 选择极其轻量的 Python 3.10 作为基础镜像 (瘦身版)
# FROM python:3.10-slim
FROM m.daocloud.io/docker.io/library/python:3.10-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制依赖清单并安装 (利用 Docker 的缓存机制加速构建)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 把你的核心代码复制进容器
COPY data_pipeline.py .
COPY llm_engine.py .
COPY main.py .

# 5. 指定容器启动时执行的命令
CMD ["python", "main.py"]