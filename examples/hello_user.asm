org 0
data:
	hello_name: .word "Hello! How is your name?\nHello, ", 0
	last: .word "!\n", 0
org 0
start:
	mov esi, hello_name ; загружаем адрес строки в eax
	xor eax, eax ; очистка счётчика
loop_a:
	; вывод приветственных слов
	cmp (esi), 0 ; проверяем, что не достигли конца строки
	jz loop_b ; иначе заканчиваем цикл
	mov eax, (esi) ; записываем символ в аккумулятор
	out ; сохраняем символ из eax в устройстве вывода (2047)
	inc esi ; инкрементируем счётчик
	jmp loop_a ; продолжаем цикл
loop_b:
	; считывание и вывод входных данных
	in ; загружаем ввод (2046) в eax
	cmp eax, 10 ; проверяем, что не достигли конца строки
	jz end_loop_b ; иначе заканчиваем цикл
	out ; сохраняем символ из eax в устройстве вывода (2047)
	jmp loop_b ; продолжаем цикл
end_loop_b:
	xor esi, esi ; очистка счётчика
	mov esi, last ; загружаем адрес строки в eax
loop_c:
	; вывод последних символов
	cmp (esi), 0 ; проверяем, что не достигли конца строки
	jz end_loop_c ; иначе заканчиваем цикл
	mov eax, (esi) ; записываем символ в аккумулятор
	out ; сохраняем символ из eax в устройстве вывода (2047)
	inc esi ; инкрементируем счётчик
	jmp loop_c ; продолжаем цикл
end_loop_c:
	hlt