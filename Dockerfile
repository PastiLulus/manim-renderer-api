FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get -y upgrade && \
    apt-get install -y build-essential libcairo2-dev libpango1.0-dev pkg-config ffmpeg curl sox \
    texlive texlive-latex-base texlive-latex-extra texlive-fonts-extra texlive-latex-recommended texlive-science \
    texlive-lang-chinese texlive-xetex fonts-noto-cjk fontconfig htop

RUN fc-cache -fv

COPY . /app

RUN pip install --upgrade pip
RUN pip install typing_extensions numpy

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

ENV FLASK_RUN_HOST=0.0.0.0

ENV FLASK_APP=run.py
ENV MANIM_LATEX_ENGINE=xelatex

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "3", "--timeout", "3600", "run:app"]
