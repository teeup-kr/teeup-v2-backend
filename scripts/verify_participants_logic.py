#!/usr/bin/env python3
"""인원수 계산 로직 검증"""

def get_required_participants(meeting_number):
    """
    모임 번호에 따라 필요한 참가자 수 계산
    48개 모임을 순서대로 나머지 0, 1, 2, 3 패턴으로 반복
    """
    # 12개씩 그룹으로 나누고, 각 그룹 내에서 4씩 증가
    group = (meeting_number - 1) // 12
    position_in_group = (meeting_number - 1) % 12
    
    # 각 그룹의 시작값: 4, 16, 28, 40
    base = 4 + (group * 12)
    
    # 그룹 내 위치에 따라 추가: 0,1,2,3,4,5,6,7,8,9,10,11
    return base + position_in_group

print("=" * 70)
print("모임 번호별 인원수 및 나머지 검증")
print("=" * 70)
print()

# 1-48번 모임 검증
for i in range(1, 49):
    count = get_required_participants(i)
    remainder = count % 4
    print(f"{i:2d}번: {count:2d}명 (나머지 {remainder})", end="  ")
    if i % 4 == 0:
        print()

print()
print("=" * 70)
print("나머지별 분류:")
print("=" * 70)

remainder_0 = [get_required_participants(i) for i in range(1, 49) if get_required_participants(i) % 4 == 0]
remainder_1 = [get_required_participants(i) for i in range(1, 49) if get_required_participants(i) % 4 == 1]
remainder_2 = [get_required_participants(i) for i in range(1, 49) if get_required_participants(i) % 4 == 2]
remainder_3 = [get_required_participants(i) for i in range(1, 49) if get_required_participants(i) % 4 == 3]

print(f"나머지 0 (4의 배수): {remainder_0}")
print(f"나머지 1: {remainder_1}")
print(f"나머지 2: {remainder_2}")
print(f"나머지 3: {remainder_3}")

print()
print("=" * 70)
print("주석과 비교:")
print("=" * 70)
print("주석: 나머지 0 -> 4, 8, 12, 16, 20, 24, 28, 32명")
print(f"실제: 나머지 0 -> {remainder_0[:8]}")
print()
print("주석: 나머지 1 -> 5, 9, 13, 17, 21, 25, 29, 33명")
print(f"실제: 나머지 1 -> {remainder_1[:8]}")
print()
print("주석: 나머지 2 -> 6, 10, 14, 18, 22, 26, 30, 34명")
print(f"실제: 나머지 2 -> {remainder_2[:8]}")
print()
print("주석: 나머지 3 -> 7, 11, 15, 19, 23, 27, 31, 35명")
print(f"실제: 나머지 3 -> {remainder_3[:8]}")















