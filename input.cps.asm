.data
str0: .asciiz " is even!\n"
str1: .asciiz " is Odd!\n"

.text
.globl main

main:
    # Llamar a func_main (tu función principal)
    jal func_main
    
    # Salir del programa (syscall exit)
    li $v0, 10
    syscall

func_main:
    # === PRÓLOGO func_main ===
    addiu $sp, $sp, -8
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO func_main ===

    # === CUERPO ===
    # Function func_main body
    li $t0, 0    # t0 = 0
    move $t1, $t0    # i = t0
L0:
    move $t2, $t1    # t1 = i
    li $t3, 30    # t2 = 30
    slt $t4, $t2, $t3    # t3 = t1 < t2
    bne $t4, $zero, L1    # if t3 goto L1
    j L3    # goto L3
L1:
    move $t5, $t1    # t7 = i
    li $t6, 2    # t8 = 2
    div $t7, $t5, $t6    # t7%t8
    mfhi $t7    # (remainder)
    move $t8, $t7    # mod = t9
    move $t9, $t1    # t10 = i
    li $v0, 1    # print int
    move $a0, $t9    # print($t9)
    syscall
    move $s0, $t8    # t11 = mod
    li $s1, 0    # t12 = 0
    seq $s2, $s0, $s1    # t13 = t11 == t12
    bne $s2, $zero, L4    # if t13 goto L4
    j L5    # goto L5
L4:
    la $s3, str0    # t14 = (str)" is even!\n"
    li $v0, 4    # print string
    move $a0, $s3    # print($s3)
    syscall
    j L6    # goto L6
L5:
    la $s4, str1    # t15 = (str)" is Odd!\n"
    li $v0, 4    # print string
    move $a0, $s4    # print($s4)
    syscall
    j L6    # goto L6
L6:
    j L2    # goto L2
L2:
    move $s5, $t1    # t4 = i
    li $s6, 1    # t5 = 1
    add $s7, $s5, $s6    # t6 = t4 + t5
    move $t1, $s7    # i = t6
    j L0    # goto L0
L3:

    # === EPÍLOGO func_main ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra	# ret en $v0
    # === FIN EPÍLOGO func_main ===

