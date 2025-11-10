# suffcal

This programm will download instagram posts from a specific user and tries to extract event information from the captions using a large language model. Now you will be up to date with all events around you!

Recommending [fest_in_aussicht](https://www.instagram.com/fest_in_aussicht/) for german users around the wunderschönen Raum Bodensee-Oberschwaben. Alle below example is based in this user.

## Setup

What you need:
- Instagram account (to access instagram posts)
- Huggingface account (to access large language models)
- Docker (recommended) or Python 3.13+ with virtualenv
- CPU only docker container, install torch with gpu support if you have a compatible GPU

I highly recommend to use the docker image for easy setup. Just build or pull the image and run it.

### Using Docker

Download the prebuilt image from the github container registry (`docker pull ghcr.io/floskinner/suffcal:latest`) or build it yourself (`docker build -t suffcal .`).

Use the provided `docker-compose.yml` file to run the container. You need to provide instagram and calendar credentials as environment variables. See the `docker-compose.yml` file for details. I would recommend to create a `.env` file to store your credentials. Also adjust the `INSTA_TARGET_USER` and `CALENDAR_NAME` variables as needed.

Run the container with `docker-compose up -d`.

## Using the project without docker
Clone the repository and install the project with [`uv`](https://github.com/astral-sh/uv) to create a virtual environment and install dependencies:

```bash
uv sync --no-dev --frozen
uv run suffcal --help
```
