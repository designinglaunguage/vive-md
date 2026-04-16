# [44] OLaLa: 대규모 언어모델 기반 온톨로지 매칭

- 영문 제목: OLaLa: Ontology Matching with Large Language Models
- 연도: 2023
- 원문 링크: https://doi.org/10.1145/3587259.3627571
- DOI: 10.1145/3587259.3627571
- 원문 저장 상태: not_downloaded
- 원문 파일: N/A
- 번역 상태: ok

## 원문(추출 텍스트)

Ontology (and more generally: Knowledge Graph) Matching is a challenging task where information in natural language is one of the most important signals to process. With the rise of Large Language Models, it is possible to incorporate this knowledge in a better way into the matching pipeline. A number of decisions still need to be taken, e.g., how to generate a prompt that is useful to the model, how information in the KG can be formulated in prompts, which Large Language Model to choose, how to provide existing correspondences to the model, how to generate candidates, etc. In this paper, we present a prototype that explores these questions by applying zero-shot and few-shot prompting with multiple open Large Language Models to different tasks of the Ontology Alignment Evaluation Initiative (OAEI). We show that with only a handful of examples and a well-designed prompt, it is possible to achieve results that are en par with supervised matching systems which use a much larger portion of the ground truth.

## 한국어 번역

온톨로지(더 일반적으로는 지식 그래프) 매칭은 자연어로 된 정보가 처리해야 할 가장 중요한 신호 중 하나인 어려운 작업입니다. 대규모 언어 모델의 등장으로 이러한 지식을 더 나은 방식으로 일치 파이프라인에 통합하는 것이 가능해졌습니다. 예를 들어, 모델에 유용한 프롬프트를 생성하는 방법, KG의 정보를 프롬프트에서 어떻게 공식화할 수 있는지, 어떤 대형 언어 모델을 선택할지, 모델에 기존 대응을 제공하는 방법, 후보를 생성하는 방법 등 많은 결정을 내려야 합니다. 이 문서에서는 OAEI(Ontology Alignment Evaluation Initiative)의 다양한 작업에 여러 개방형 대형 언어 모델을 사용한 제로 샷 및 소수 샷 프롬프트를 적용하여 이러한 질문을 탐색하는 프로토타입을 제시합니다. 우리는 단지 소수의 예시와 잘 설계된 프롬프트를 사용하여 실제 정보의 훨씬 더 많은 부분을 사용하는 지도 매칭 시스템과 동등한 결과를 얻을 수 있음을 보여줍니다.
