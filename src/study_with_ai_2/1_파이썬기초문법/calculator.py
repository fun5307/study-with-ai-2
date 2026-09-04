def total_expense(*args):
    """여러 지출 금액 입력받아 최종 지출 금액을 반환하는 함수"""
    return f"최종 지출 금액: {sum(args)}원"

def remain(budget,expenses):
    """예산과 현재 지출 금액 받아 남은 예산 반환하는 함수"""
    return f"남은 예산: {budget-expenses}원"

def discount(expenses, rate):
    """지출 금액과 할인율(%)을 받아 할인된 금액을 반환하는 함수"""
    dc_ratio = (100-rate)/100
    return f"할인된 금액: {expenses*dc_ratio}원"