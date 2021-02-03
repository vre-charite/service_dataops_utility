FROM 10.32.42.225:5000/python:3.7-buster
USER root
WORKDIR /usr/src/app

# set timezone
ENV TZ=America/Toronto
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get update --proxy="http://proxy.charite.de:8080/"
RUN apt-get install -y vim --proxy="http://proxy.charite.de:8080/"
RUN apt-get install -y less --proxy="http://proxy.charite.de:8080/"
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt --proxy="http://proxy.charite.de:8080/"
COPY . .
CMD ["./gunicorn_starter.sh"]
