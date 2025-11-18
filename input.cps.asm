.data
str0: .asciiz ", "
str1: .asciiz "\nAfter:\n"

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
    addiu $sp, $sp, -268
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

    li $t1, 1    # t1 = 1
    li $t8, 1
    li $t9, 4
    mul $t2, $t8, $t9    # t2 = 1 * 4
    add $t3, $t0, $t2    # t3 = t0 + t2
    sw $t1, 0($t3)
    li $t4, 3    # t4 = 3
    li $t8, 2
    li $t9, 4
    mul $t5, $t8, $t9    # t5 = 2 * 4
    add $t6, $t0, $t5    # t6 = t0 + t5
    sw $t4, 0($t6)
    li $t7, 51    # t7 = 51
    li $t8, 3
    li $t9, 4
    mul $s0, $t8, $t9    # t8 = 3 * 4
    add $s1, $t0, $s0    # t9 = t0 + t8
    sw $t7, 0($s1)
    li $s2, 76    # t10 = 76
    li $t8, 4
    li $t9, 4
    mul $s3, $t8, $t9    # t11 = 4 * 4
    add $s4, $t0, $s3    # t12 = t0 + t11
    sw $s2, 0($s4)
    li $s5, 182    # t13 = 182
    li $t8, 5
    li $t9, 4
    mul $s6, $t8, $t9    # t14 = 5 * 4
    add $s7, $t0, $s6    # t15 = t0 + t14
    sw $s5, 0($s7)
    sw $t1, -164($fp)    # spill t1
    li $t1, 7    # t16 = 7
    li $t8, 6
    li $t9, 4
    sw $t2, -12($fp)    # spill t2
    mul $t2, $t8, $t9    # t17 = 6 * 4
    sw $t0, -152($fp)    # spill t0
    add $t0, $t0, $t2    # t18 = t0 + t17
    sw $t1, 0($t0)
    sw $t0, -120($fp)    # spill t18
    sw $t1, -168($fp)    # spill t16
    sw $t1, 0($t0)
    lw $t0, -152($fp)    # reload t0
    sw $t0, -152($fp)    # spill t0
    li $t1, 0    # t19 = 0
    sw $t1, -16($fp)    # spill t19
L0:
    sw $t2, -200($fp)    # spill t17
    move $t2, $t1    # t20 = i
    sw $t3, -236($fp)    # spill t3
    li $t3, 6    # t21 = 6
    sw $t2, -176($fp)    # spill t20
    slt $t2, $t2, $t3    # t22 = t20 < t21
    bne $t2, $zero, L1    # if t22 goto L1
    j L3    # goto L3
L1:
    sw $t2, -204($fp)    # spill t22
    move $t2, $t1    # t26 = i
    li $t8, 1
    sw $t2, -160($fp)    # spill t26
    add $t2, $t2, $t8    # t28 = t26 + 1
    li $t8, 4
    sw $t2, -92($fp)    # spill t28
    mul $t2, $t2, $t8    # t29 = t28 * 4
    sw $t2, -256($fp)    # spill t29
    add $t2, $t0, $t2    # t30 = arr + t29
    sw $t2, -244($fp)    # spill t30
    lw $t2, 0($t2)
    sw $t2, -108($fp)    # spill t27
    li $v0, 1    # print int
    move $a0, $t2    # print($t2)
    syscall
    # t32 = (str)", " -> str0
    li $v0, 4    # print string
    la $a0, str0    # print(t32)
    syscall
    j L2    # goto L2
L2:
    sw $t1, -8($fp)    # spill i
    sw $t2, -260($fp)    # spill t31
    li $t2, 1    # t24 = 1
    sw $t1, -192($fp)    # spill t23
    add $t1, $t1, $t2    # t25 = t23 + t24
    sw $t1, -68($fp)    # spill t25
    j L0    # goto L0
L3:
    # t33 = (str)"\nAfter:\n" -> str1
    li $v0, 4    # print string
    la $a0, str1    # print(t33)
    syscall
    sw $t1, -8($fp)    # spill i
    li $t1, 0    # t34 = 0
    sw $t1, -20($fp)    # spill t34
L4:
    sw $t2, -40($fp)    # spill t24
    move $t2, $t1    # t35 = j
    sw $t3, -224($fp)    # spill t21
    li $t3, 6    # t36 = 6
    sw $t2, -24($fp)    # spill t35
    slt $t2, $t2, $t3    # t37 = t35 < t36
    bne $t2, $zero, L5    # if t37 goto L5
    j L7    # goto L7
L5:
    sw $t2, -44($fp)    # spill t37
    move $t2, $t1    # t41 = j
    li $t8, 1
    sw $t2, -180($fp)    # spill t41
    add $t2, $t2, $t8    # t42 = t41 + 1
    sw $t3, -72($fp)    # spill t36
    move $t3, $t1    # t43 = j
    li $t8, 4
    sw $t2, -52($fp)    # spill t42
    mul $t2, $t2, $t8    # t44 = t42 * 4
    sw $t2, -220($fp)    # spill t44
    add $t2, $t0, $t2    # t45 = arr + t44
    sw $t3, 0($t2)
    j L6    # goto L6
L6:
    sw $t1, -104($fp)    # spill j
    sw $t2, -156($fp)    # spill t45
    li $t2, 1    # t39 = 1
    sw $t1, -28($fp)    # spill t38
    add $t1, $t1, $t2    # t40 = t38 + t39
    sw $t1, -36($fp)    # spill t40
    j L4    # goto L4
L7:
    sw $t1, -104($fp)    # spill j
    li $t1, 0    # t46 = 0
    sw $t1, -248($fp)    # spill t46
L8:
    sw $t2, -76($fp)    # spill t39
    move $t2, $t1    # t47 = k
    sw $t3, -80($fp)    # spill t43
    li $t3, 6    # t48 = 6
    sw $t2, -84($fp)    # spill t47
    slt $t2, $t2, $t3    # t49 = t47 < t48
    bne $t2, $zero, L9    # if t49 goto L9
    j L11    # goto L11
L9:
    sw $t2, -216($fp)    # spill t49
    move $t2, $t1    # t53 = k
    li $t8, 1
    sw $t2, -136($fp)    # spill t53
    add $t2, $t2, $t8    # t55 = t53 + 1
    li $t8, 4
    sw $t2, -56($fp)    # spill t55
    mul $t2, $t2, $t8    # t56 = t55 * 4
    sw $t2, -88($fp)    # spill t56
    add $t2, $t0, $t2    # t57 = arr + t56
    sw $t2, -252($fp)    # spill t57
    lw $t2, 0($t2)
    sw $t2, -48($fp)    # spill t54
    li $v0, 1    # print int
    move $a0, $t2    # print($t2)
    syscall
    # t59 = (str)", " -> str0
    li $v0, 4    # print string
    la $a0, str0    # print(t59)
    syscall
    j L10    # goto L10
L10:
    sw $t1, -208($fp)    # spill k
    sw $t2, -172($fp)    # spill t58
    li $t2, 1    # t51 = 1
    sw $t1, -184($fp)    # spill t50
    add $t1, $t1, $t2    # t52 = t50 + t51
    sw $t1, -148($fp)    # spill t52
    j L8    # goto L8
L11:

    # === EPÍLOGO func_main ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 268
    jr $ra	# ret en $v0
    # === FIN EPÍLOGO func_main ===

