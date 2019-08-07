FROM ubuntu:18.04

RUN echo "deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic main restricted universe multiverse\n\
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-security main restricted universe multiverse\n\
deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-updates main restricted universe multiverse" > /etc/apt/sources.list

RUN apt-get update && \
	apt-get install --no-install-recommends -y python3 python3-dev python3-pip python3-setuptools && \
	rm -rf /var/lib/apt/lists/*

RUN pip3 install boto3 django django-extensions requests && \
	rm -rf ~/.cache/pip

WORKDIR /app/mediaserver

EXPOSE 80
CMD ["python3", "manage.py", "runserver", "0.0.0.0:80"]
