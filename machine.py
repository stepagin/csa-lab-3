import logging
import sys

from isa import *


class DataPath:
    eax = None  # аккумуляторный регистр (accumulator register)
    ebx = None  # базовый регистр (base register)
    ecx = None  # счетный регистр (count register)
    edx = None  # регистр данных (data register)
    esi = None  # указатель источника (source index register)
    edi = None  # указатель приемника (destination index register)
    ebp = None  # указатель базы стека (base pointer register)
    esp = None  # указатель стека (stack pointer register)

    negative_flag = None
    zero_flag = None
    carry_flag = None

    data_memory = None
    "Память данных. Инициализируется нулевыми значениями."

    data_address = None
    "Адрес в памяти данных. Инициализируется нулём."

    input_buffer = None
    "Буфер входных данных. Инициализируется входными данными конструктора."

    output_buffer = None
    "Буфер выходных данных."

    def __init__(self, init_memory, input_buffer):
        self.eax = 0
        self.esp = 2045
        self.data_memory = [0] * 2048
        for m in init_memory:
            assert m.get('index', None) is not None and m.get("value", None) is not None, "internal error"
            self.data_memory[m.get('index')] = m.get("value")
        self.data_address = 0
        self.input_buffer = input_buffer
        self.output_buffer = []

    def _write_to_reg(self, reg, value):
        if reg == "eax":
            self.eax = value
        elif reg == "ebx":
            self.ebx = value
        elif reg == "ecx":
            self.ecx = value
        elif reg == "edx":
            self.edx = value
        elif reg == "esi":
            self.esi = value
        elif reg == "edi":
            self.edi = value
        elif reg == "ebp":
            self.ebp = value
        elif reg == "esp":
            self.esp = value

    def signal_latch_data_addr(self, sel):
        assert 0 <= sel <= 2046, "internal error, incorrect selector: {}".format(sel)
        self.data_address = sel

    def signal_data_latch_reg(self, reg):
        """Защёлкнуть слово из памяти (`oe` от Output Enable) и защёлкнуть его в
        регистр. Сигнал `oe` выставляется неявно `ControlUnit`-ом.
        read from data to reg
        """
        if self.data_address == 2046:
            if len(self.input_buffer) == 0:
                raise EOFError()
            symbol_code = ord(self.input_buffer.pop(0))
            assert INT_MIN <= symbol_code <= INT_MAX, "input token is out of bound: {}".format(symbol_code)

            self._write_to_reg(reg, symbol_code)
        else:
            self._write_to_reg(reg, self.data_memory[self.data_address])

    def zero(self):
        return self.zero_flag

    def carry(self):
        return self.carry_flag

    def neg(self):
        return self.negative_flag

    def take_out_value(self, reg):
        """
        Взятие значения из регистра
        """
        d = {
            "eax": self.eax,
            "ebx": self.ebx,
            "ecx": self.ecx,
            "edx": self.edx,
            "esi": self.esi,
            "edi": self.edi,
            "ebp": self.ebp,
            "esp": self.esp,
        }
        return d.get(reg, None)

    def signal_wr_in_data(self, val):
        assert 0 <= val <= 2047, "data address out of bound"
        if self.data_address == 2047:
            self.signal_output(val)
        self.data_memory[self.data_address] = val

    def signal_wr_in_reg(self, reg, val):
        assert reg in existing_registers
        self._write_to_reg(reg, val)
        self._handle_overflow(reg)

    def signal_output(self, val):
        symbol = chr(val)
        logging.debug("output: %s << %s", repr("".join(self.output_buffer)), repr(symbol))
        self.output_buffer.append(symbol)

    def _handle_overflow(self, reg):
        val = self.take_out_value(reg)
        if val > INT_MAX:
            self._write_to_reg(reg, val - 2 * INT_MAX + 1)
        elif INT_MIN > val:
            self._write_to_reg(reg, val + 2 * INT_MAX + 1)


class ControlUnit:
    instruction_memory = None
    "Память команд."

    program_counter = None
    "Счётчик команд. Инициализируется нулём."

    data_path = None
    "Блок обработки данных."

    _tick = None
    "Текущее модельное время процессора (в тактах). Инициализируется нулём."

    _index_mapping = None
    "соотношение индексов в памяти команд и индексов в списке program"

    def __init__(self, program, data_path: DataPath, init_pc=0):
        self.program = program
        self._index_mapping = dict()
        for i in range(len(program)):
            self._index_mapping[program[i]["index"]] = i
        self.program_counter = init_pc
        self.data_path = data_path
        self._tick = 0

    def _get_instr(self, i):
        return self.program[self._index_mapping.get(i, Command("nop").to_dict())]

    def tick(self):
        """Продвинуть модельное время процессора вперёд на один такт."""
        self._tick += 1

    def current_tick(self):
        """Текущее модельное время процессора (в тактах)."""
        return self._tick

    def signal_latch_program_counter(self, sel_next):
        """Защёлкнуть новое значение счётчика команд.

        Если `sel_next` равен `True`, то счётчик будет увеличен на единицу,
        иначе -- будет установлен в значение аргумента текущей инструкции.
        """
        if sel_next:
            self.program_counter += 1
        else:
            instr = self._get_instr(self.program_counter)
            assert "operand1" in instr, "internal error"

            self.program_counter = instr["operand1"]

    def decode_and_execute_control_flow_instruction(self, instr, opcode):
        """Декодировать и выполнить инструкцию управления потоком исполнения. В
        случае успеха -- вернуть `True`, чтобы перейти к следующей инструкции.
        """
        if opcode is Opcode.HALT:
            raise StopIteration()

        if opcode is Opcode.JMP:
            addr = instr["operand1"]
            self.program_counter = addr
            self.tick()

            return True

        elif opcode is Opcode.JZ:
            # self.data_path.signal_data_latch_reg()
            # self.tick()

            if self.data_path.zero():
                self.signal_latch_program_counter(sel_next=False)
            else:
                self.signal_latch_program_counter(sel_next=True)
            self.tick()

            return True

        elif opcode is Opcode.JNZ:
            # self.data_path.signal_data_latch_reg()
            # self.tick()

            if not self.data_path.zero():
                self.signal_latch_program_counter(sel_next=False)
            else:
                self.signal_latch_program_counter(sel_next=True)
            self.tick()

            return True

        elif opcode is Opcode.JMC:
            # self.data_path.signal_data_latch_reg()
            # self.tick()

            if self.data_path.carry():
                self.signal_latch_program_counter(sel_next=False)
            else:
                self.signal_latch_program_counter(sel_next=True)
            self.tick()

            return True

        elif opcode is Opcode.JMNC:
            # self.data_path.signal_data_latch_reg()
            # self.tick()

            if not self.data_path.carry():
                self.signal_latch_program_counter(sel_next=False)
            else:
                self.signal_latch_program_counter(sel_next=True)
            self.tick()

            return True

        elif opcode is Opcode.JLT:
            # self.data_path.signal_data_latch_reg()
            # self.tick()

            if self.data_path.neg():
                self.signal_latch_program_counter(sel_next=False)
            else:
                self.signal_latch_program_counter(sel_next=True)
            self.tick()

            return True

        elif opcode is Opcode.JGT:
            # self.data_path.signal_data_latch_reg()
            # self.tick()

            if not self.data_path.neg() and not self.data_path.zero():
                self.signal_latch_program_counter(sel_next=False)
            else:
                self.signal_latch_program_counter(sel_next=True)
            self.tick()

            return True

        return False

    def get_reg_or_value(self, reg_or_value: str):
        """
        Преобразует строку в число и при необходимости достаёт
        значение из регистров
        """
        if reg_or_value.isdigit():
            return int(reg_or_value)
        res = self.data_path.take_out_value(reg_or_value)
        assert res is not None, f"unknown value: {reg_or_value}"
        return res

    def decode_and_execute_instruction(self):
        instr = self._get_instr(self.program_counter)

        opcode = instr["opcode"]
        if self.decode_and_execute_control_flow_instruction(instr, opcode):
            return

        op1_addressed = False
        op2_addressed = False
        op1 = instr.get("operand1", None)
        if op1 is not None:
            op1_addressed = in_parentheses(op1)
            op1 = remove_parentheses(op1)

        op2 = instr.get("operand2", None)
        if op2 is not None:
            op2_addressed = in_parentheses(op2)
            op2 = remove_parentheses(op2)

        assert not (op1_addressed and op2_addressed), "error: double memory access"

        if opcode == Opcode.MOV:

            if not op1_addressed:
                # запись в регистр
                if op2_addressed:
                    self.data_path.signal_latch_data_addr(self.get_reg_or_value(op2))
                    self.data_path.signal_data_latch_reg(op1)
                else:
                    op2 = self.get_reg_or_value(op2)
                    self.data_path.signal_wr_in_reg(op1, op2)
                self.tick()
            else:
                # запись по адресу из первого операнда
                op1 = self.get_reg_or_value(op1)
                self.data_path.signal_latch_data_addr(op1)
                op2 = self.get_reg_or_value(op2)
                self.data_path.signal_wr_in_data(op2)
                self.tick()

        elif opcode in [Opcode.INC, Opcode.DEC]:
            assert not op1_addressed, "internal error"
            assert op1 in existing_registers, "internal error"
            sign = (1 if opcode == Opcode.INC else -1)
            self.data_path.signal_wr_in_reg(op1, self.data_path.take_out_value(op1) + sign)

        elif opcode in [Opcode.ADD, Opcode.SUB]:
            assert not op1_addressed and op1 in existing_registers, "internal error"
            if op2_addressed:
                self.data_path.signal_latch_data_addr(int(op2))
                sign = (1 if opcode == Opcode.ADD else -1)
                op2 = sign * self.data_path.data_memory[self.get_reg_or_value(op2)]
                self.data_path.signal_wr_in_reg(op1, self.data_path.take_out_value(op1) + op2)
                self.tick()
            else:
                op2 = self.get_reg_or_value(op2) * (1 if opcode == Opcode.ADD else -1)
                self.data_path.signal_wr_in_reg(op1, self.data_path.take_out_value(op1) + op2)

        elif opcode == Opcode.XOR:
            assert not op1_addressed, "error: double memory access"
            if op1 == op2 and not op2_addressed:
                self.data_path.signal_wr_in_reg(op1, 0)
            elif op2_addressed:
                op2 = self.get_reg_or_value(op2)
                self.data_path.signal_latch_data_addr(op2)
                self.data_path.signal_wr_in_reg(op1, self.get_reg_or_value(op1) ^ self.data_path.data_memory[op2])
            else:
                self.data_path.signal_wr_in_reg(op1, self.get_reg_or_value(op1) ^ self.get_reg_or_value(op2))

        elif opcode == Opcode.CMP:
            assert not (op1_addressed and op2_addressed), "error: double memory access"
            if op1_addressed:
                op1 = self.get_reg_or_value(op1)
                self.data_path.signal_latch_data_addr(op1)
                op1 = self.data_path.data_memory[op1]
                self.tick()
            else:
                op1 = self.get_reg_or_value(op1)
            if op2_addressed:
                op2 = self.get_reg_or_value(op2)
                self.data_path.signal_latch_data_addr(op2)
                op2 = self.data_path.data_memory[op2]
            else:
                op2 = self.get_reg_or_value(op2)
            res = op1 - op2
            self.data_path.zero_flag = res == 0
            self.data_path.negative_flag = res < 0

        elif opcode == Opcode.ASR:
            assert not op1_addressed, "internal error"
            assert op1 in existing_registers, "internal error"

            self.data_path.carry_flag = bool(self.data_path.take_out_value(op1) % 2)
            self.data_path.signal_wr_in_reg(op1, self.data_path.take_out_value(op1) // 2)
            self.tick()

        elif opcode in [Opcode.MOD, Opcode.DIV]:
            assert not op1_addressed, "error: double memory access"
            if op2_addressed:
                op2 = self.get_reg_or_value(op2)
                self.data_path.signal_latch_data_addr(op2)
                if opcode == Opcode.MOD:
                    self.data_path.signal_wr_in_reg(op1, self.get_reg_or_value(op1) % self.data_path.data_memory[op2])
                else:
                    self.data_path.signal_wr_in_reg(op1, self.get_reg_or_value(op1) // self.data_path.data_memory[op2])
            else:
                if opcode == Opcode.MOD:
                    self.data_path.signal_wr_in_reg(op1, self.get_reg_or_value(op1) % self.get_reg_or_value(op2))
                else:
                    self.data_path.signal_wr_in_reg(op1, self.get_reg_or_value(op1) // self.get_reg_or_value(op2))
            self.tick()

        if opcode != Opcode.CMP and op1 in existing_registers:
            self.data_path.zero_flag = self.get_reg_or_value(op1) == 0
            self.data_path.negative_flag = self.get_reg_or_value(op1) < 0

        self.signal_latch_program_counter(sel_next=True)
        self.tick()

    def __repr__(self):
        """Вернуть строковое представление состояния процессора."""
        state_repr = "TICK: {:3} PC: {:3} ADDR: {:3} MEM_OUT: {} EAX({}), EBX({}), ECX({}), " \
                     "EDX({}), ESI({}), EDI({}), EBP({}), ESP({})".format(
            self._tick,
            self.program_counter,
            self.data_path.data_address,
            self.data_path.data_memory[self.data_path.data_address],
            self.data_path.eax,
            self.data_path.ebx,
            self.data_path.ecx,
            self.data_path.edx,
            self.data_path.esi,
            self.data_path.edi,
            self.data_path.ebp,
            self.data_path.esp
        )

        instr = self._get_instr(self.program_counter)
        opcode = instr["opcode"]
        instr_repr = str(opcode)

        if "operand1" in instr:
            instr_repr += f" {instr['operand1']}"

        if "operand2" in instr:
            instr_repr += f" {instr['operand2']}"

        return "{} \t{}".format(state_repr, instr_repr)


def simulation(code, input_tokens, data_memory, pc):
    data_path = DataPath(data_memory, input_tokens)
    control_unit = ControlUnit(code, data_path, init_pc=pc)
    instr_counter = 0

    logging.debug("%s", control_unit)
    try:
        while True:
            control_unit.decode_and_execute_instruction()
            instr_counter += 1
            logging.debug("%s", control_unit)
    except EOFError:
        logging.warning("Input buffer is empty!")
    except StopIteration:
        pass

    logging.info("output_buffer: %s", repr("".join(data_path.output_buffer)))

    return "".join(data_path.output_buffer), instr_counter, control_unit.current_tick()


def main(code_file, input_file):
    """Функция запуска модели процессора. Параметры -- имена файлов с машинным
    кодом и с входными данными для симуляции.
    """
    code, start_pc = read_code(code_file)
    with open(input_file, encoding="ascii") as file:
        input_text = file.read()
        input_token = []
        for char in input_text:
            input_token.append(char)

    output, instr_counter, ticks = simulation(
        code.get("instruction_memory"),
        input_tokens=input_token,
        data_memory=code.get("data_memory"),
        pc=start_pc
    )

    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
