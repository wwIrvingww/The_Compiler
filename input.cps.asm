.text
.globl main

main:
    # Llamar a func_main (tu función principal)
    jal func_main
    
    # Salir del programa (syscall exit)
    li $v0, 10
    syscall

func_fib:
    # === PRÓLOGO func_fib ===
    addiu $sp, $sp, -20
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO func_fib ===

    # === CUERPO ===
    # Function func_fib body
    move $t0, $a0    # $t0 = param[0]
    sw $a0, 8($sp)
    move $t1, $t0    # t0 = n
    li $t2, 1    # t1 = 1
    sle $t3, $t1, $t2    # t2 = t0 <= t1
    bne $t3, $zero, L0    # if t2 goto L0
    j L1    # goto L1
L0:
    move $t4, $t0    # t3 = n
    move $v0, $t4    # return t3
    j L2    # goto L2
L1:
    move $t5, $t0    # t4 = n
    li $t6, 1    # t5 = 1
    sub $t7, $t5, $t6    # t6 = t4 - t5
    move $a0, $t7    # param[0] = t6
    jal func_fib   # call func_fib()
    move $t8, $v0    # ret of func_fib()
    move $t9, $t8    # t8 = t7
    move $s0, $t0    # t9 = n
    li $s1, 2    # t10 = 2
    sub $s2, $s0, $s1    # t11 = t9 - t10
    move $a0, $s2    # param[0] = t11
    jal func_fib   # call func_fib()
    move $s3, $v0    # ret of func_fib()
    move $s4, $s3    # t13 = t12
    add $s5, $t9, $s4    # t14 = t8 + t13
    move $s6, $s5    # val = t14
    move $s7, $s6    # t15 = val
    li $v0, 1    # print int
    move $a0, $s7    # print($s7)
    syscall
    move $t0, $s6    # t16 = val
    move $v0, $t0    # return t16
    j L2    # goto L2
L2:

    # === EPÍLOGO func_fib ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 20
    jr $ra	# ret en $v0
    # === FIN EPÍLOGO func_fib ===


func_main:
    # === PRÓLOGO func_main ===
    addiu $sp, $sp, -8
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO func_main ===

    # === CUERPO ===
    # Function func_main body
    li $t0, 10    # t17 = 10
    move $a0, $t0    # param[0] = t17
    jal func_fib   # call func_fib()
    move $t1, $v0    # ret of func_fib()
    move $t2, $t1    # t19 = t18
    move $t3, $t2    # ret = t19
    move $t4, $t3    # t20 = ret
    li $v0, 1    # print int
    move $a0, $t4    # print($t4)
    syscall

    # === EPÍLOGO func_main ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra	# ret en $v0
    # === FIN EPÍLOGO func_main ===

