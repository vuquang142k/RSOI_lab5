FROM --platform=linux/amd64 python:3.9
COPY . /gateway-service
COPY requirements.txt /gateway-service
WORKDIR /gateway-service
RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["python3", "gateway-service.py"]