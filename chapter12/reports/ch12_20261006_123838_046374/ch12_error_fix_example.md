
[분석 목적]
completed 주문의 카테고리별·월별 금액을 집계하고,
같은 범위에서 기준 총합과 집계 총합을 비교하려고 합니다.

[필요한 데이터 구조]
orders: order_id, order_date, order_status
order_items: order_id, product_id, line_total
products: product_id, category

[오류 당시의 Evidence]
FK 문제 행 제외 후 orders는 298행, order_items는 745행입니다.
주문 날짜 결측·변환 실패는 3건이며, 이 중 completed는 2건입니다.
날짜 제외 전 completed 주문 상세 금액은 140,888,000입니다.

[문제를 확인하는 최소 코드]
parsed_dates = pd.to_datetime(orders["order_date"], errors="coerce")
invalid_dates = parsed_dates.isna()
assert not invalid_dates.any(), "날짜 문제가 발견됐습니다."

[오류 메시지]
AssertionError: 날짜 문제가 발견됐습니다.

[요청]
1. 이 오류의 원인을 설명해 주세요.
2. 날짜를 임의로 채우지 않는 처리 방안을 제안해 주세요.
3. 원본을 보존하고 제외 행 수와 금액을 기록해 주세요.
4. 카테고리·월별 집계 범위를 일치시키는 방법을 제안해 주세요.
5. 실행이나 새 패키지 설치 없이 코드와 검증 기준만 제안해 주세요.
