FROM --platform=linux/amd64 python:3.9
COPY . /ticket-service
COPY requirements.txt /ticket-service
WORKDIR /ticket-service
RUN pip install -r requirements.txt
EXPOSE 8060
CMD ["python3", "ticket-service.py"]