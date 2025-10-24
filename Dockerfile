# Sử dụng một image Python chính thức làm base image
FROM python:3.10-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Sao chép requirements.txt và cài đặt các phụ thuộc
COPY requirements /app/requirements

# Cài đặt các thư viện từ requirements.txt
RUN pip install --no-cache-dir -r /app/requirements

# Sao chép mã nguồn vào container
COPY . /app

# Cấu hình cho Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Mở cổng 5000 cho Flask
EXPOSE 5000

# Lệnh chạy Flask
CMD ["flask", "run", "--host=0.0.0.0"]
