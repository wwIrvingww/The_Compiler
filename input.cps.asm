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
    addiu $sp, $sp, -104
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO func_fib ===

    # === CUERPO ===
    # Function func_fib body
    move $t0, $a0    # $t0 = param[0]
    move $t1, $t0    # t0 = n
    li $t2, 1    # t1 = 1
    sle $t3, $t1, $t2    # t2 = t0 <= t1
    bne $t3, $zero, L0    # if t2 goto L0
    j L1    # goto L1
L0:
    li $t4, 1    # t3 = 1
    move $v0, $t4    # return t3
    j L2    # goto L2
L1:
    move $t5, $t0    # t4 = n
    li $t6, 1    # t5 = 1
    sub $t7, $t5, $t6    # t6 = t4 - t5
    move $a0, $t7    # param[0] = t6
    jal func_fib   # call func_fib()
    move $s0, $v0    # ret of func_fib()
    move $s1, $s0    # t8 = t7
    move $s2, $s1    # a = t8
    move $s3, $t0    # t9 = n
    li $s4, 2    # t10 = 2
    sub $s5, $s3, $s4    # t11 = t9 - t10
    move $a0, $s5    # param[0] = t11
    jal func_fib   # call func_fib()
    move $s6, $v0    # ret of func_fib()
    move $s7, $s6    # t13 = t12
    sw $t0, -32($fp)    # spill n
    move $t0, $s7    # b = t13
    sw $t1, -84($fp)    # spill t0
    move $t1, $s2    # t14 = a
    sw $t0, -56($fp)    # spill b
    sw $t0, -68($fp)    # spill t15
    add $t0, $t1, $t0    # t16 = t14 + t15
    move $v0, $t0    # return t16
    j L2    # goto L2
L2:

    # === EPÍLOGO func_fib ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 104
    jr $ra	# ret en $v0
    # === FIN EPÍLOGO func_fib ===


func_main:
    # === PRÓLOGO func_main ===
    addiu $sp, $sp, -32
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
    move $t3, $t2    # f = t19
    move $t4, $t3    # t20 = f
    li $v0, 1    # print int
    move $a0, $t4    # print($t4)
    syscall

    # === EPÍLOGO func_main ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 32
    jr $ra	# ret en $v0
    # === FIN EPÍLOGO func_main ===

