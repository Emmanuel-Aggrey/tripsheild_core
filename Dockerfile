FROM python:3.12

WORKDIR /opt

ADD . /opt

RUN pip install --upgrade pip && \
pip install -r requirements.txt

EXPOSE 8002