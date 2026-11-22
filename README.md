# Assist News


[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
![버전 1.0.0](https://img.shields.io/badge/version-v1.0.0-blue.svg?style=for-the-badge)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Me-F16061?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/plplaaa2)

Assist News는 네이버 언론사별 주요 뉴스를 Home Assistant Assist에서 들을 수 있게 해주는 HACS 사용자 정의 통합입니다.

뉴스 기사의 저작권은 각 기사를 발행한 언론사에 있습니다.

## 기능

- 네이버 언론사 ID로 언론사를 여러 개 등록하고, 각 언론사를 Assist 도구 제공자로 선택할 수 있습니다.
- 기사 제목은 원문 그대로 읽고, 본문은 기본적으로 차분한 아나운서 말투로 요약합니다. 여러 기사를 읽을 때는 “첫 소식입니다”, “이어서 다음 소식입니다” 같은 연결 멘트를 씁니다.
- 브리핑은 육하원칙에 따라 누가, 언제, 어디서, 무엇을, 어떻게, 왜에 해당하는 사실을 전합니다. 본문에 없는 항목은 생략합니다.
- 기본적으로 가져온 모든 기사를 순서대로 브리핑합니다. 사용자가 더 적은 개수나 특정 기사 선별을 요청하면 해당 요청을 따릅니다.
- 말투를 지정하면 해당 요청을 따르며, 기사 링크는 요청할 때만 제공합니다.

## 설치

### HACS 설치 (권장)

[![Home Assistant Marketplace에서 Assist News 열기](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=plplaaa2&repository=assist_naver_news&category=integration)

HACS에서 직접 추가하려면 [Assist News 저장소](https://github.com/plplaaa2/assist_naver_news)를 사용자 지정 저장소에 등록하고 유형으로 **통합**을 선택합니다. Assist News를 설치한 뒤 Home Assistant를 재시작합니다.

### 수동 설치

`custom_components/assist_news/` 폴더를 Home Assistant 설정 폴더 아래의 `custom_components/`에 복사한 뒤 Home Assistant를 재시작합니다.

## 설정

### 네이버 뉴스 언론사 번호 찾기

1. [네이버 뉴스 언론사 목록](https://media.naver.com/press)에서 원하는 언론사의 이름이나 로고를 누릅니다.
2. 브라우저 주소창에서 `/press/` 바로 뒤의 숫자를 확인합니다. 예를 들어 [연합뉴스](https://media.naver.com/press/001)의 언론사 ID는 `001`입니다. 앞의 `0`까지 그대로 입력하세요.

### 통합 추가

1. **설정 → 기기 및 서비스 → 통합 추가 → Assist News**에서 네이버 언론사 ID를 입력합니다. 예를 들어 [연합뉴스](https://media.naver.com/press/001)의 ID는 `001`입니다.
2. 사용할 언론사마다 통합 항목을 추가합니다.
3. Assist에서 사용하는 LLM 대화 에이전트의 도구 제공자 또는 Home Assistant API 설정에서 **〈언론사 이름〉 뉴스**를 활성화합니다. 메뉴 이름은 대화 에이전트에 따라 다를 수 있습니다.

| 언론사별 설정 | 기본값 | 범위 |
| --- | ---: | ---: |
| 주요 기사 수 | 12개 | 1~30개 |
| 기사당 가져올 본문 길이 | 1,000자 | 100~10,000자 |
| 기사별 요약 브리핑 목표 길이 | 100자 | 30~500자 |

## 음성 요청 예시

- “연합뉴스 주요 뉴스 세 개를 알려줘.”
- “오늘 주요 뉴스를 아나운서처럼 읽어줘.”
- “첫 번째 기사 링크를 알려줘.”

## 라이선스

Assist News 프로젝트 코드는 [MIT 라이선스](LICENSE)를 따릅니다.
