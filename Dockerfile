FROM python:3.10-slim
RUN apt-get update && apt-get install -y git
WORKDIR /app
RUN git clone https://github.com/kaifcode/freefire-like-and-guest-api.git .
COPY main.py .
COPY requirements.txt .
EXPOSE 8080
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]
