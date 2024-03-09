import json
import re
from enum import Enum

regex = {
    "label": re.compile(r"\A([a-zA-Z_]+):"),
    "address": re.compile(r"\Aorg\s+(\d+)\Z"),
    "const": re.compile(r"\.word\s+(\d+|\".+\"(?:\s*,\s*(?:\d+|\".+\"))*)\Z"),
    "unaddressed": re.compile(r"\A([a-zA-Z]+)\Z"),
    "addressed": re.compile(r"\A([a-zA-Z]+)\s+([()a-zA-Z0-9_]+)(?:,\s+([()a-zA-Z0-9_]+))?\Z")
}

INT_MAX = 2147483647
INT_MIN = -2147483648

jump_opcodes = ["jmp", "jz", "jnz", "jlt", "jgt", "jmc", "jmnc"]
one_operand_opcodes = ["inc", "dec", "push", "pop", "asr"] + jump_opcodes
two_operand_opcodes = ["mov", "add", "sub", "xor", "cmp", "mod", "div"]
addressed_opcodes = one_operand_opcodes + two_operand_opcodes
unaddressed_opcodes = ["nop", "in", "out", "hlt"]
existing_registers = ["eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"]


def in_parentheses(text):
    if len(text) < 2:
        return False
    return text[0] == "(" and text[-1] == ")"


def remove_parentheses(text):
    if text[0] == "(" and text[-1] == ")":
        return text[1:-1]
    return text


class Opcode(str, Enum):
    NOP = "nop"

    MOV = "mov"
    INC = "inc"
    DEC = "dec"
    ADD = "add"
    SUB = "sub"
    XOR = "xor"
    CMP = "cmp"
    ASR = "asr"
    MOD = "mod"
    DIV = "div"

    JMP = "jmp"
    JZ = "jz"
    JNZ = "jnz"
    JMC = "jmc"
    JMNC = "jmnc"
    JLT = "jlt"
    JGT = "jgt"

    HALT = "hlt"

    def __str__(self):
        return str(self.value)


class Operand:
    name = None
    addressed = None

    def __init__(self, op: str):
        if op in existing_registers or op.isdigit():
            self.name = op
            self.addressed = False
        else:
            op = remove_parentheses(op)
            if op in existing_registers or op.isdigit():
                self.name = op
                self.addressed = True
        assert self.name is not None, f"operand does not exist: {op}"

    def __str__(self):
        return f"({self.name})" if self.addressed else self.name


class Command:
    opcode = None
    op1 = None
    op2 = None

    def __init__(self, opcode: str):
        self.opcode = Opcode(opcode)

    def set_operand1(self, op1: str):
        self.op1 = Operand(op1)
        return self

    def set_operand2(self, op2: str):
        assert self.op1 is not None, f"operand1 must be defied before operand2: {self.opcode}"
        self.op2 = Operand(op2)
        return self

    def to_dict(self):
        command = dict()
        command["opcode"] = str(self.opcode)
        if self.op1 is not None:
            command["operand1"] = str(self.op1)
        if self.op2 is not None:
            command["operand2"] = str(self.op2)
        return command


def write_code(filename, code):
    """Записать машинный код в файл."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write('{\n\t"data_memory": [\n\t\t')
        f.write(",\n\t\t".join(json.dumps(i) for i in code["data_memory"]))
        f.write("\n\t],\n")
        f.write('\t"instruction_memory": [\n\t\t')
        f.write(",\n\t\t".join(json.dumps(i) for i in code["instruction_memory"]))
        f.write("\n\t]\n}")


def read_code(filename):
    with open(filename, encoding="utf-8") as file:
        code = json.loads(file.read())

    for instr in code.get("instruction_memory"):
        # Конвертация строки в Opcode
        instr["opcode"] = Opcode(instr["opcode"])
    start_pc = 0
    if len(code.get("instruction_memory")) > 0:
        start_pc = code.get("instruction_memory")[0].get("index", 0)
    return code, start_pc


if __name__ == "__main__":
    print("Это служебный файл.")
