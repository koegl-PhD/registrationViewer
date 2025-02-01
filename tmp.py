class Case():
    def __init__(self, current_case: int, case_count: int):
        self.current_case = current_case
        self.case_count = case_count

    def __str__(self):
        return f"Case {self.current_case}{self.case_count}"


print(Case(1, 2))
