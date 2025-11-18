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
    # === Save parameters to stack ===
    sw $a0, -4($fp)    # Save n
    # Guardar registros $s
    sw $s0, 8($sp)
    sw $s1, 12($sp)
    sw $s2, 16($sp)
    sw $s3, 20($sp)
    sw $s4, 24($sp)
    # === FIN PRÓLOGO func_fib ===

    # === CUERPO ===
    # Function func_fib body
    move $s0, $a0    # $s0 = param[0]
    sw $s0, -84($fp)
    move $t0, $s0    # t0 = n
    li $t1, 1    # t1 = 1
    sle $t2, $t0, $t1    # t2 = t0 <= t1
    bne $t2, $zero, L0    # if t2 goto L0
    j L1    # goto L1
L0:
    li $t3, 1    # t3 = 1
    move $v0, $t3    # return t3
    j L2    # goto L2
L1:
    move $t4, $s0    # t4 = n
    li $t5, 1    # t5 = 1
    sub $t6, $t4, $t5    # t6 = t4 - t5
    move $a0, $t6    # param[0] = t6
    jal func_fib   # call func_fib()
    move $t7, $v0    # ret of func_fib()
    move $t8, $t7    # t8 = t7
    move $s1, $t8    # a = t8
    move $t9, $s0    # t9 = n
    sw $t0, -36($fp)    # spill t0
    li $t0, 2    # t10 = 2
    sw $t0, -68($fp)    # spill t10
    sub $t0, $t9, $t0    # t11 = t9 - t10
    move $a0, $t0    # param[0] = t11
    jal func_fib   # call func_fib()
    sw $t0, -32($fp)    # spill t11
    move $t0, $v0    # ret of func_fib()
    move $s2, $t0    # b = t13
    sw $t0, -44($fp)    # spill t13
    move $t0, $s1    # t14 = a
    sw $t1, -80($fp)    # spill t1
    move $t1, $s2    # t15 = b
    sw $t0, -60($fp)    # spill t14
    add $t0, $t0, $t1    # t16 = t14 + t15
    move $v0, $t0    # return t16
    j L2    # goto L2
L2:

    # === EPÍLOGO func_fib ===
    # Guardar registros $s
    lw $s4, 24($sp)
    lw $s3, 20($sp)
    lw $s2, 16($sp)
    lw $s1, 12($sp)
    lw $s0, 8($sp)
    # Restaurar $ra y $fp del caller
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 104
    jr $ra	# ret en $v0
    # === FIN EPÍLOGO func_fib ===


func_main:
    # === PRÓLOGO func_main ===
    addiu $sp, $sp, -24
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # Guardar registros $s
    sw $s0, 8($sp)
    # === FIN PRÓLOGO func_main ===

    # === CUERPO ===
    # Function func_main body
    li $t0, 10    # t17 = 10
    move $a0, $t0    # param[0] = t17
    jal func_fib   # call func_fib()
    move $t1, $v0    # ret of func_fib()
    move $t2, $t1    # t19 = t18
    li $v0, 1    # print int
    move $a0, $t2    # print($t2)
    syscall

    # === EPÍLOGO func_main ===
    # Guardar registros $s
    lw $s0, 8($sp)
    # Restaurar $ra y $fp del caller
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 24
    jr $ra	# ret en $v0
    # === FIN EPÍLOGO func_main ===

