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
    addiu $sp, $sp, -112
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO func_main ===

    # === CUERPO ===
    # Function func_main body

    # == CREATE ARRAY (t0) == #
    li $v0, 9    # srbk (heap)
    li $a0, 1024    # Fixed limit -> 256 elements
    syscall
    move $t0, $v0    # t0 = new Array
    # == END CREATE ARRAY == #

    li $t1, 13    # t1 = 13
    li $t2, 1
    li $t3, 4
    mul $t4, $t2, $t3    # t2 = 1 * 4
    add $t5, $t0, $t4    # t3 = t0 + t2
    sw $t1, 0($t5)
    li $t6, 67    # t4 = 67
    li $t7, 2
    li $t3, 4
    mul $t8, $t7, $t3    # t5 = 2 * 4
    add $t9, $t0, $t8    # t6 = t0 + t5
    sw $t6, 0($t9)
    li $s0, 42    # t7 = 42
    li $s1, 3
    li $t3, 4
    mul $s2, $s1, $t3    # t8 = 3 * 4
    add $s3, $t0, $s2    # t9 = t0 + t8
    sw $s0, 0($s3)
    sw $s1, 0($t0)
    move $s4, $t0    # arr = t0
    li $s5, 0    # t10 = 0
    move $s6, $s5    # i = t10
L0:
    move $s7, $s6    # t11 = i
    sw $t0, -92($fp)    # spill t0
    li $t0, 4    # t12 = 4
    sw $t0, -96($fp)    # spill t12
    slt $t0, $s7, $t0    # t13 = t11 < t12
    bne $t0, $zero, L1    # if t13 goto L1
    j L3    # goto L3
L1:
    sw $t0, -32($fp)    # spill t13
    move $t0, $s6    # t17 = i
    li $t2, 1
    sw $t0, -100($fp)    # spill t17
    add $t0, $t0, $t2    # t19 = t17 + 1
    li $t3, 4
    sw $t0, -88($fp)    # spill t19
    mul $t0, $t0, $t3    # t20 = t19 * 4
    sw $t0, -56($fp)    # spill t20
    add $t0, $s4, $t0    # t21 = arr + t20
    sw $t0, -84($fp)    # spill t21
    lw $t0, 0($t0)
    sw $t0, -104($fp)    # spill t18
    li $v0, 1    # print int
    move $a0, $t0    # print($t0)
    syscall
    j L2    # goto L2
L2:
    sw $t0, -24($fp)    # spill t22
    move $t0, $s6    # t14 = i
    sw $t1, -64($fp)    # spill t1
    li $t1, 1    # t15 = 1
    sw $t0, -40($fp)    # spill t14
    add $t0, $t0, $t1    # t16 = t14 + t15
    move $s6, $t0    # i = t16
    j L0    # goto L0
L3:

    # === EPÍLOGO func_main ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 112
    jr $ra	# ret en $v0
    # === FIN EPÍLOGO func_main ===

