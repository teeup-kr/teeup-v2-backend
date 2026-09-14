"""
활성 서비스 이용약관(SERVICE)에 콘텐츠 신고·차단·이용 제한 조항(제7조 제1항 아·자호, 제2항, 제7조의2)을 추가한다.

App Store Guideline 1.2 — "terms must make it clear that there is no tolerance for
objectionable content or abusive users".

이미 조항이 들어 있으면 아무것도 하지 않는다 (멱등).

실행:
    .venv/bin/python scripts/update_terms_ugc_clause.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal  # noqa: E402
from models.enums import TermsType  # noqa: E402
from models.terms import Terms  # noqa: E402

ANCHOR = "   사. 외설 또는 폭력적인 메시지, 화상, 음성, 기타 공서양속에 반하는 정보를 공개 또는 게시하는 행위<br><br>\n제8조 (개인정보보호)<br>"
MARKER = "제7조의2 (콘텐츠 신고 및 이용 제한)"
CLAUSE = """   사. 외설 또는 폭력적인 메시지, 화상, 음성, 기타 공서양속에 반하는 정보를 공개 또는 게시하는 행위<br>
   아. 타인을 비방·모욕·괴롭히거나 차별·혐오를 조장하는 행위<br>
   자. 스팸·광고, 사기·허위 정보, 타인의 개인정보를 게시하는 행위<br>
2. 회사는 제1항을 위반하는 부적절한 콘텐츠와 악성 이용자를 용인하지 않습니다.<br><br>
제7조의2 (콘텐츠 신고 및 이용 제한)<br>
1. 회원은 부적절한 클럽·모임·공지·규정 등 콘텐츠나 사용자를 서비스 내 「신고하기」 기능 또는 1:1 문의를 통해 신고할 수 있으며, 회사는 접수일로부터 24시간 이내에 확인하여 해당 콘텐츠 삭제, 이용 제한 등 필요한 조치를 취합니다.<br>
2. 회원은 「사용자 차단」 기능으로 특정 회원의 콘텐츠가 자신에게 표시되지 않도록 할 수 있으며, 언제든지 해제할 수 있습니다.<br>
3. 회사는 제7조 제1항을 위반한 회원에 대하여 사전 통지 없이 콘텐츠 삭제, 서비스 이용 정지 또는 회원 자격 상실 조치를 할 수 있습니다.<br>
4. 회사는 부적절한 표현이 포함된 콘텐츠의 등록을 사전에 제한할 수 있습니다.<br><br>
제8조 (개인정보보호)<br>"""


def main() -> int:
    db = SessionLocal()
    try:
        rows = db.query(Terms).filter(Terms.type == TermsType.SERVICE, Terms.is_active.is_(True)).all()
        if not rows:
            print("활성 SERVICE 약관이 없습니다. create_default_terms.py 를 먼저 실행하세요.")
            return 1
        for t in rows:
            if MARKER in (t.content or ""):
                print(f"[이미 적용] terms #{t.id}")
                continue
            if ANCHOR not in (t.content or ""):
                print(f"[건너뜀] terms #{t.id}: 제7조 사호/제8조 앵커를 찾을 수 없어 수동 편집이 필요합니다.")
                continue
            t.content = t.content.replace(ANCHOR, CLAUSE)
            db.commit()
            print(f"[적용 완료] terms #{t.id}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
