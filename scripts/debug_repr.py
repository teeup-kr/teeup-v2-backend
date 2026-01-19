#!/usr/bin/env python3
"""
repr 문제 디버깅 헬퍼
"""
from pydantic import BaseModel
from typing import Any

def find_bad_repr_on_model(Model, sample=None):
    print(f"=== Inspect {Model.__name__} fields ===")
    for name, f in Model.model_fields.items():
        try:
            _ = repr(f.annotation)  # annotation repr 시도
        except Exception as e:
            print(f"[BAD ANNOTATION REPR] field={name} type={type(f.annotation)} err={e}")

    if sample is not None:
        try:
            m = Model(**sample)
            for name, v in m.__dict__.items():
                try:
                    _ = repr(v)       # 값 repr 시도
                except Exception as e:
                    print(f"[BAD VALUE REPR] field={name} type={type(v)} err={e}")
        except Exception as e:
            print("[VALIDATION ERROR while building sample]:", e)

# 테스트할 모델들
if __name__ == "__main__":
    try:
        from schemas import ClubCreate, ClubResponse, ClubApplicationCreate
        from models import Club, ClubApplication
        
        print("=== Testing schemas ===")
        find_bad_repr_on_model(ClubCreate)
        find_bad_repr_on_model(ClubResponse)
        find_bad_repr_on_model(ClubApplicationCreate)
        
        print("\n=== Testing models ===")
        find_bad_repr_on_model(Club)
        find_bad_repr_on_model(ClubApplication)
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
