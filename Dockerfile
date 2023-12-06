FROM python:3.11

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
ENV PATH="/root/.poetry/bin:$PATH"

WORKDIR /main

COPY . .

RUN poetry install

CMD ["python", "bot.py"]
