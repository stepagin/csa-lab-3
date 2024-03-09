org 0
start:
    mov esi, 1 ; f1 = 1
    mov edi, 1 ; f2 = 1
    xor eax, eax ; в eax будет считаться следующий член f3
    xor ecx, ecx ; sum = 0
    xor edx, edx ; буффер для сохранения eax
    push 0 ; выставляем нуль для нуль-терминированного вывода
loop:
    mov eax, esi ; eax = f1
    add eax, edi ; eax += f2
    cmp eax, 4000000 ; если eax больше 4_000_000
    jgt number_push ; то выходим из цикла

    ; иначе проверяем на чётность
    mov edx, eax ; сохраняем значение аккумулятора в edx
    asr eax ; сдвигаем значение аккумулятора побитово вправо, eax[0] -> C
    mov eax, edx ; восстанавливаем значение аккумулятора из edx
    jmc calc ; если последний бит был 1, то пропускаем суммирование

    ; добавляем f3 в сумму
    add ecx, eax ; sum += f3
calc:
    mov esi, edi ; f1 = f2
    mov edi, eax ; f2 = f3
    jmp loop ; продолжаем цикл

number_push: ; выводим сумму на устройство вывода
	mov edx, ecx ; d = sum
	mod edx, 10 ; d = d mod 10
	add edx, 48 ; делаем сдвиг, чтобы число стало кодом символа числа
	push edx ; сохраняем d в начало вывода
	div ecx, 10 ; sum = sum div 10
	cmp ecx, 0 ; если сумма ещё не равна 0
	jgt number_push ; то выводим ещё цифру на экран
number_pop:
    pop edx ; достаём первый символ
    cmp edx, 0 ; если он равен нулю
    jz end ; то заканчиваем вывод
    mov (2047), edx ; иначе вывести на экран символ
    jmp number_pop ; продолжить вывод

end:
    hlt ; останавливаем программу