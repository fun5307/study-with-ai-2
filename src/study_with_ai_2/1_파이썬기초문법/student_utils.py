def 학생_소개(**info):
    for key, value in info.items():
        print(key, ":", value)

def 합격_여부(score):
    if score >= 60:
        return "합격"
    else:
        return "불합격"
