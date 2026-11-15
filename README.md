# Assist News

[English](./README.md) | [한국어](./README.ko.md)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
![Version 1.0.0](https://img.shields.io/badge/version-v1.0.0-blue.svg?style=for-the-badge)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Me-F16061?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/plplaaa2)

Assist News is a custom Home Assistant integration that lets Assist read top stories from Naver News publishers.

Copyright in each news article belongs to its respective publisher.

## Features

- Register multiple Naver News publishers and enable each as a separate Assist tool provider.
- Hear original headlines and short summaries in a calm news anchor style by default. You can also request a different delivery style.
- Ask for article links when you want them.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=plplaaa2&repository=assist_naver_news&category=integration)

You can also add the [Assist News repository](https://github.com/plplaaa2/assist_naver_news) as a custom HACS repository in the **Integration** category. Install Assist News, then restart Home Assistant.

### Manual installation

Copy the `custom_components/assist_news/` directory into `custom_components/` under your Home Assistant configuration directory, then restart Home Assistant.

## Setup

### Find the Naver News publisher ID

1. Open the [Naver News publisher directory](https://media.naver.com/press) and select the publisher you want.
2. Copy the digits immediately after `/press/` in the address bar. For [Yonhap News](https://media.naver.com/press/001), the ID is `001`. Keep the leading zeros.

### Add the integration

1. Go to **Settings → Devices & services → Add integration → Assist News** and enter the Naver publisher ID. For example, [Yonhap News](https://media.naver.com/press/001) uses `001`.
2. Add one integration entry per publisher.
3. Enable **〈publisher name〉 뉴스** in the tool provider or Home Assistant API settings for the LLM conversation agent used by Assist. Menu names vary by agent.

| Per-publisher setting | Default | Range |
| --- | ---: | ---: |
| Number of top stories | 12 | 1–30 |
| Article body length | 1,000 characters | 100–10,000 |
| Target summary length per story | 100 characters | 30–500 |

## Example voice requests

- “Read three top stories from Yonhap News.”
- “Read today’s headlines like a news anchor.”
- “Give me the link to the first article.”
