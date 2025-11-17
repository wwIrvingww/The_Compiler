.data
str0: .asciiz ", "

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

    # == CREATE ARRAY (t0) == #
    li $v0, 9    # srbk (heap)
    li $a0, 1024    # Fixed limit -> 256 elements
    syscall
    move $t0, $v0    # t0 = new Array
    # == END CREATE ARRAY == #

    li $t1, 5    # t1 = 5
    li $t2, 1
    li $t3, 4
    mul $t4, $t2, $t3    # t2 = 1 * 4
    add $t5, $t0, $t4    # t3 = t0 + t2
    sw $t1, 0($t5)
    li $t6, 1    # t4 = 1
    li $t7, 2
    li $t3, 4
    mul $t8, $t7, $t3    # t5 = 2 * 4
    add $t9, $t0, $t8    # t6 = t0 + t5
    sw $t6, 0($t9)
    li $s0, 32    # t7 = 32
    li $s1, 3
    li $t3, 4
    mul $s2, $s1, $t3    # t8 = 3 * 4
    add $s3, $t0, $s2    # t9 = t0 + t8
    sw $s0, 0($s3)
    li $s4, 745    # t10 = 745
    li $t3, 4
    li $t3, 4
    mul $s5, $t3, $t3    # t11 = 4 * 4
    add $s6, $t0, $s5    # t12 = t0 + t11
    sw $s4, 0($s6)
    li $s7, 42    # t13 = 42
    sw $t1, -56($fp)    # spill t1
    li $t1, 5
    li $t3, 4
    mul $t1, $t1, $t3    # t14 = 5 * 4
    sw $t0, -36($fp)    # spill t0
    add $t0, $t0, $t1    # t15 = t0 + t14
    sw $s7, 0($t0)
    sw $t0, -112($fp)    # spill t15
    sw $t0, 0($t0)
    sw $t0, -36($fp)    # spill t0
    sw $t1, -88($fp)    # spill t14
    li $t1, 0    # t16 = 0
    sw $t1, -124($fp)    # spill t16
L0:
    move $t2, $t1    # t17 = i
    li $t3, 5    # t18 = 5
    sw $t2, -28($fp)    # spill t17
    slt $t2, $t2, $t3    # t19 = t17 < t18
    bne $t2, $zero, L1    # if t19 goto L1
    j L3    # goto L3
L1:
    sw $t2, -108($fp)    # spill t19
    move $t2, $t1    # t23 = i
    sw $t2, -32($fp)    # spill t23
    li $t2, 1
    add $t2, $t2, $t2    # t25 = t23 + 1
    sw $t2, -40($fp)    # spill t25
    li $t2, 4
    mul $t2, $t2, $t2    # t26 = t25 * 4
    sw $t2, -92($fp)    # spill t26
    add $t2, $t0, $t2    # t27 = arr + t26
    sw $t2, -60($fp)    # spill t27
    lw $t2, 0($t2)
    sw $t2, -128($fp)    # spill t24
    li $v0, 1    # print int
    move $a0, $t2    # print($t2)
    syscall
    sw $t2, -52($fp)    # spill t28
    la $t2, str0    # t29 = (str)", "
    li $v0, 4    # print string
    move $a0, $t2    # print($t2)
    syscall
    j L2    # goto L2
L2:
    sw $t1, -68($fp)    # spill i
    sw $t2, -104($fp)    # spill t29
    li $t2, 1    # t21 = 1
    sw $t1, -96($fp)    # spill t20
    add $t1, $t1, $t2    # t22 = t20 + t21
    sw $t1, -132($fp)    # spill t22
    j L0    # goto L0
L3:

    # === EPÍLOGO func_main ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra	# ret en $v0
    # === FIN EPÍLOGO func_main ===

