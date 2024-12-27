FROM --platform=linux/amd64 python:3.9
COPY . /bonus-service
COPY requirements.txt /bonus-service
WORKDIR /bonus-service
RUN pip install -r requirements.txt
EXPOSE 8050
CMD ["python3", "bonus-service.py"]