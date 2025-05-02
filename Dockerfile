FROM python:3.12

WORKDIR /code

COPY requirements.txt /code/requirements.txt
RUN pip install -r /code/requirements.txt

COPY src/salamanders_api.py /code/salamanders_api.py
COPY src/worker.py /code/worker.py
COPY src/jobs.py /code/jobs.py

ENV PATH="/code:$PATH"

EXPOSE 5000

CMD ["python", "/code/salamanders_api.py"]
