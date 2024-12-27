FROM --platform=linux/amd64 python:3.9
COPY . /flight-service
COPY requirements.txt /flight-service
WORKDIR /flight-service
RUN pip install -r requirements.txt
EXPOSE 8060
CMD ["python3", "flight-service.py"]