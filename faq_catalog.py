from dataclasses import dataclass


@dataclass
class Question:
    question: str
    answer: str


def download_faq(filename: str) -> list[Question]:
    with open(filename, encoding="utf8") as file:
        content = file.readlines()
        questions: list[Question] = []

        for line in range(0, len(content) - 1, 2):
            questions.append(Question(question=content[line].strip(), answer=content[line + 1].strip()))

        return questions


if __name__ == "__main__":
    download_faq("assets/texts/faq.txt")
