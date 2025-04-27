FROM python:3.10-slim

WORKDIR /tur

COPY ./requirements.txt .

RUN pip install -r requirements.txt

COPY ./ .
 
 
ENV PORT 8080
 
 
EXPOSE 8080
 
 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]