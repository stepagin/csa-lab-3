org 0
start:
loop:
	; считывание и вывод входных данных
	in ; загружаем ввод (2046) в eax
	cmp eax, 0 ; проверяем, что не достигли конца строки
	jz end_loop ; иначе заканчиваем цикл
	out ; сохраняем символ из eax в устройстве вывода (2047)
	jmp loop ; продолжаем цикл
end_loop:
	hlt