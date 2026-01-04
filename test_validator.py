from state.state_schema import SectionStateValidator
from pydantic import ValidationError
import sys

def test():
    print("Testing Validator...")
    
    # 1. Valid Case
    try:
        SectionStateValidator(
            chapter_index=1,
            target_words=500,
            current_words=0,
            section_index="1.1"
        )
        print("Valid case passed.")
    except Exception as e:
        print(f"FAILED: Valid case raised unexpected error: {e}")
        sys.exit(1)

    # 2. Invalid Index
    try:
        SectionStateValidator(
            chapter_index=1,
            target_words=500,
            current_words=0,
            section_index="invalid"
        )
        print("FAILED: Invalid index did NOT raise ValidationError")
        sys.exit(1)
    except ValidationError:
        print("Invalid index caught (Expected).")
    except Exception as e:
        print(f"FAILED: Invalid index raised wrong error type: {type(e)}")
        sys.exit(1)

    # 3. Invalid Negative
    try:
        SectionStateValidator(
            chapter_index=-1,
            target_words=500,
            current_words=0,
            section_index="1.1"
        )
        print("FAILED: Negative index did NOT raise ValidationError")
        sys.exit(1)
    except ValidationError:
        print("Negative index caught (Expected).")
    except Exception as e:
        print(f"FAILED: Negative index raised wrong error type: {type(e)}")
        sys.exit(1)

    print("SUCCESS")

if __name__ == "__main__":
    try:
        test()
    except Exception as e:
        print(f"FAILED: Script crashed: {e}")
        sys.exit(1)
