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

Setting PADDLE_OCR_BASE_DIR to set the default ocr model cache path.

## Setting HF Token
If models are not downloaded, set HF_TOKEN to your hugging-face token
