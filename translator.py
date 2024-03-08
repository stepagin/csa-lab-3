import sys

from isa import *

section_data = []
data_labels = dict()
section_code = []
code_labels = dict()


def get_label(line):
    expr = regex.get("label")
    match = expr.search(line)
    if match is None:
        return None
    return match.group(1).lower()


def get_const(line):
    expr = regex.get("const")
    match = expr.search(line)
    if match is None:
        return None

    match = match.group(1)
    assert match.count('"') % 2 == 0, "odd number of quotation marks, line: {}".format(line)
    res = []
    i = 0
    while i < len(match):
        if match[i] == '"':
            i += 1
            res.append('"')
            while match[i] != '"':
                if match[i] == '\\':
                    if match[i + 1] == 'n':
                        i += 1
                        res.append('\n')
                    elif match[i + 1] == 't':
                        i += 1
                        res.append('\t')
                else:
                    res += [match[i]]
                i += 1
            res.append('"')
        elif match[i] == ",":
            res += ["\\,"]
        else:
            res += [match[i]]
        i += 1
    return [t.strip() for t in "".join(res).split(r"\,")]


def get_address(line):
    expr = regex.get("address")
    match = expr.search(line)
    if match is None:
        return None
    return match.group(1)


def get_command(line):
    addr_expr = regex.get("addressed")
    unaddr_expr = regex.get("unaddressed")
    addr_match = addr_expr.search(line)
    unaddr_match = unaddr_expr.search(line)

    if unaddr_match is not None:
        command = dict()
        command["opcode"] = unaddr_match.group(1).lower()
        return command
    elif addr_match is not None:
        command = dict()
        command["opcode"] = addr_match.group(1).lower()
        command["operand1"] = addr_match.group(2).lower()
        if addr_match.group(3) is not None:
            command["operand2"] = addr_match.group(3).lower()
        return command
    else:
        return None


def check_command(command, line_number):
    opcode = command.get("opcode", None)
    if opcode is None:
        return False
    operand1 = command.get("operand1", None)
    # operand2 может быть регистром, адресом или числом
    operand2 = command.get("operand2", None)

    # проверка безадресной команды
    if opcode in unaddressed_opcodes:
        assert operand1 is None and operand2 is None, \
            'expecting no arguments: "{}", line: {}'.format(opcode, line_number)
        return True

    # проверка адресной команды с одним операндом
    elif opcode in one_operand_opcodes:
        assert operand1 is not None and operand2 is None, \
            'expecting one argument: "{}", line: {}'.format(opcode, line_number)

        if opcode == "push":
            operand = remove_parentheses(operand1)
            assert operand.isdigit() or operand in existing_registers or operand in data_labels.keys(), \
                'unknown push operand: "{}", line: {}'.format(operand, line_number)
            del operand
            return True

        if opcode in ["asr", "inc", "dec"]:
            assert operand1 in existing_registers, 'operand must be one of registers, line: {}'.format(line_number)

        if opcode in jump_opcodes:
            assert not operand1.isdigit() and not in_parentheses(operand1), \
                "jumps only works with labels in code, line: {}".format(line_number)
            assert operand1 not in data_labels, \
                "jumps only works with labels in code, line: {}".format(line_number)
            return True

        if remove_parentheses(operand1) in existing_registers:
            return True

        if remove_parentheses(operand1).isdigit():
            assert not operand1.isdigit(), \
                'this command does not work with numbers: "{}", line: {}'.format(opcode, line_number)
        else:
            assert operand1 in data_labels, 'unknown operand: "{}", line: {}'.format(operand1, line_number)

    # проверка адресной команды с двумя операндами
    elif opcode in two_operand_opcodes:
        assert operand1 is not None and operand2 is not None, \
            'expecting two arguments: "{}", line: {}'.format(opcode, line_number)

        if opcode in ["mod", "div"]:
            assert operand1 in existing_registers, 'operand1 must be one of registers, line: {}'.format(line_number)

        assert not operand1.isdigit(), 'first operand must not be a number: "{}", line: {}'.format(opcode, line_number)
        assert not (in_parentheses(operand1) and in_parentheses(operand2)), \
            "you cant access data memory twice in one command"
        operand1 = remove_parentheses(operand1)
        operand2 = remove_parentheses(operand2)
        assert not (operand1 in code_labels.keys() or operand2 in code_labels.keys()), \
            'operand must not be a label in code: "{}", line: {}'.format(opcode, line_number)

        assert (operand1.isdigit() or operand1 in existing_registers or operand1 in data_labels), \
            'unknown operand: "{}", line: {}'.format(operand1, line_number)
        assert (operand2.isdigit() or operand2 in existing_registers or operand2 in data_labels), \
            'unknown operand: "{}", line: {}'.format(operand2, line_number)

        return True

    return False


def save_command(index, command):
    section_code.append({**{"index": index}, **command})


def translate(text):
    global section_code, section_data
    global code_labels, data_labels
    line_number = 1
    pc = 0
    data_processing = False

    while line_number <= len(text):
        line = text[line_number - 1].split(";", 1)[0].strip()  # выбираем только значимый текст без комментариев

        # взятие адреса из строки
        address = get_address(line)
        if address is not None:
            assert 0 <= int(address) < 2045, "address out of bound: {}, line: {}".format(pc, line_number)
            pc = int(address)
            line_number += 1
            continue

        # взятие метки из строки
        label_name = get_label(line)
        if label_name is not None:
            if label_name == "data":
                data_processing = True
            elif label_name == "start":
                assert code_labels.get(label_name, None) is None, f'"start" label already exists, line: {line_number}'
                data_processing = False
            # сохранение
            if data_processing:
                data_labels[label_name] = pc
            else:
                code_labels[label_name] = pc
            # удаление label из line:
            line = line[line.find(":") + 1:].strip()

        # взятие константы из строки
        const = get_const(line)
        if const is not None:
            assert data_processing, 'missing "data" label, line: {}'.format(line_number)
            # обработка констант
            for c in const:
                assert c.isdigit() or c[0] == '"' and c[-1] == '"', "invalid const: {}, line: {}".format(c, line_number)
                if c.isdigit():
                    section_data.append({"index": pc, "value": int(c)})
                    pc += 1
                else:
                    for char in c[1:-1]:
                        section_data.append({"index": pc, "value": ord(char)})
                        pc += 1

        # взятие команды из строки
        command = get_command(line)
        if command is not None:
            opcode = command.get("opcode")
            operand1 = command.get("operand1")
            assert not data_processing, 'missing "start" label, line: {}'.format(line_number)
            assert check_command(command, line_number), 'command does not exist: "{}", line: {}'.format(
                line,
                line_number
            )

            if opcode == "in":
                command = Command("mov").set_operand1("eax").set_operand2("(2046)").to_dict()
            elif opcode == "out":
                command = Command("mov").set_operand1("(2047)").set_operand2("eax").to_dict()
            elif opcode == "pop":
                command = Command("mov").set_operand1(operand1).set_operand2("(esp)").to_dict()
                save_command(pc, command)
                pc += 1
                command = Command("inc").set_operand1("esp").to_dict()
            elif opcode == "push":
                command = Command("dec").set_operand1("esp").to_dict()
                save_command(pc, command)
                pc += 1
                command = Command("mov").set_operand1("(esp)").set_operand2(operand1).to_dict()
            save_command(pc, command)
            pc += 1

        # проверка на корректность введённой строки
        if address is None and line != "":
            if data_processing:
                assert const is not None, \
                    'unknown data line: "{}", line: {}'.format(line, line_number)
            else:
                assert command is not None, \
                    'unknown command: "{}", line: {}'.format(line, line_number)

        line_number += 1

    has_halt = False
    for i in range(len(section_code)):
        opcode = section_code[i].get("opcode", None)
        operand1 = section_code[i].get("operand1", None)
        operand2 = section_code[i].get("operand2", None)
        if opcode == "hlt":
            has_halt = True
        if opcode in jump_opcodes:
            assert operand1 in code_labels, 'operand must be a label in code: "{} {}"'.format(opcode, operand1)
        if opcode in two_operand_opcodes:
            assert operand1 not in code_labels and operand2 not in code_labels, \
                'operands must not be a label in code: "{} {}, {}"'.format(opcode, operand1, operand2)
        if operand1 is not None:
            if operand1 in code_labels:
                section_code[i]["operand1"] = code_labels[operand1]
            elif remove_parentheses(operand1) in data_labels:
                if in_parentheses(operand1):
                    section_code[i]["operand1"] = f"({data_labels[remove_parentheses(operand1)]})"
                else:
                    section_code[i]["operand1"] = str(data_labels[operand1])
            elif operand1.isdigit():
                assert INT_MIN <= int(operand1) <= INT_MAX, "integer out of bound: {}".format(operand1)
        if operand2 is not None:
            if operand2 in code_labels:
                section_code[i]["operand2"] = code_labels[operand2]
            elif remove_parentheses(operand2) in data_labels:
                if in_parentheses(operand2):
                    section_code[i]["operand2"] = f"({data_labels[remove_parentheses(operand2)]})"
                else:
                    section_code[i]["operand2"] = str(data_labels[operand2])
            elif operand2.isdigit():
                assert INT_MIN <= int(operand2) <= INT_MAX, "integer out of bound: {}".format(operand2)

    assert has_halt, "there's should be a halt command"

    return {"data_memory": section_data, "instruction_memory": section_code}


def main(code_source_filename, code_target_filename):
    with open(code_source_filename, encoding="utf-8") as f:
        code_source_array = f.read().split("\n")
    code = translate(code_source_array)
    # print(*code["instruction_memory"], sep='\n')
    write_code(code_target_filename, code)
    print("source LoC:", len(code_source_array), "code instr:", len(code))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)
