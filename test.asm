.data
str0: .asciiz "a="
str1: .asciiz " sum="
str2: .asciiz " | "
str3: .asciiz "c="
str4: .asciiz " "
str5: .asciiz " [end inner] "
str6: .asciiz "sum_else="
str8: .asciiz "FIN WHILE"

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
    move $t1, $t0    # a = t0
    li $t2, 10    # t1 = 10
    move $t3, $t2    # b = t1
    li $t4, 0    # t2 = 0
    move $t5, $t4    # sum = t2
L0:
    move $t6, $t1    # t3 = a
    move $t7, $t3    # t4 = b
    slt $t8, $t6, $t7    # t5 = t3 < t4
    move $t9, $t5    # t6 = sum
    li $s0, 50    # t7 = 50
    slt $s1, $t9, $s0    # t8 = t6 < t7
    and $s2, $t8, $s1    # t9 = t5 && t8
    bne $s2, $zero, L1    # if t9 goto L1
    j L2    # goto L2
L1:
    # t10 = (str)"a=" -> str0
    li $v0, 4    # print string
    la $a0, str0    # print(t10)
    syscall
    move $s3, $t1    # t11 = a
    li $v0, 1    # print int
    move $a0, $s3    # print($s3)
    syscall
    # t12 = (str)" sum=" -> str1
    li $v0, 4    # print string
    la $a0, str1    # print(t12)
    syscall
    move $s4, $t5    # t13 = sum
    li $v0, 1    # print int
    move $a0, $s4    # print($s4)
    syscall
    # t14 = (str)" | " -> str2
    li $v0, 4    # print string
    la $a0, str2    # print(t14)
    syscall
    move $s5, $t1    # t15 = a
    li $s6, 1    # t16 = 1
    add $s7, $s5, $s6    # t17 = t15 + t16
    move $t1, $s7    # a = t17
    # WARNING: cannot spill t0 from $t0 (no offset)
    move $t0, $t5    # t18 = sum
    # WARNING: cannot spill t1 from $t2 (no offset)
    move $t2, $t1    # t19 = a
    # WARNING: cannot spill t18 from $t0 (no offset)
    add $t0, $t0, $t2    # t20 = t18 + t19
    move $t5, $t0    # sum = t20
    # WARNING: cannot spill t20 from $t0 (no offset)
    move $t0, $t5    # t21 = sum
    # WARNING: cannot spill t19 from $t2 (no offset)
    li $t2, 30    # t22 = 30
    # WARNING: cannot spill t21 from $t0 (no offset)
    sgt $t0, $t0, $t2    # t23 = t21 > t22
    bne $t0, $zero, L6    # if t23 goto L6
    j L7    # goto L7
L6:
    # WARNING: cannot spill t23 from $t0 (no offset)
    li $t0, 0    # t24 = 0
    # WARNING: cannot spill t24 from $t0 (no offset)
L3:
    # WARNING: cannot spill t22 from $t2 (no offset)
    move $t2, $t0    # t25 = c
    # WARNING: cannot spill t2 from $t4 (no offset)
    move $t4, $t1    # t26 = a
    # WARNING: cannot spill t25 from $t2 (no offset)
    slt $t2, $t2, $t4    # t27 = t25 < t26
    bne $t2, $zero, L4    # if t27 goto L4
    j L5    # goto L5
L4:
    # t28 = (str)"c=" -> str3
    li $v0, 4    # print string
    la $a0, str3    # print(t28)
    syscall
    # WARNING: cannot spill t27 from $t2 (no offset)
    move $t2, $t0    # t29 = c
    li $v0, 1    # print int
    move $a0, $t2    # print($t2)
    syscall
    # t30 = (str)" " -> str4
    li $v0, 4    # print string
    la $a0, str4    # print(t30)
    syscall
    # WARNING: cannot spill c from $t0 (no offset)
    # WARNING: cannot spill t29 from $t2 (no offset)
    li $t2, 2    # t32 = 2
    # WARNING: cannot spill t31 from $t0 (no offset)
    add $t0, $t0, $t2    # t33 = t31 + t32
    # WARNING: cannot spill t33 from $t0 (no offset)
    j L3    # goto L3
L5:
    # t34 = (str)" [end inner] " -> str5
    li $v0, 4    # print string
    la $a0, str5    # print(t34)
    syscall
    j L8    # goto L8
L7:
    # WARNING: cannot spill c from $t0 (no offset)
    move $t0, $t5    # t35 = sum
    # WARNING: cannot spill t32 from $t2 (no offset)
    li $t2, 1    # t36 = 1
    # WARNING: cannot spill t35 from $t0 (no offset)
    add $t0, $t0, $t2    # t37 = t35 + t36
    move $t5, $t0    # sum = t37
    # t38 = (str)"sum_else=" -> str6
    li $v0, 4    # print string
    la $a0, str6    # print(t38)
    syscall
    # WARNING: cannot spill t37 from $t0 (no offset)
    move $t0, $t5    # t39 = sum
    li $v0, 1    # print int
    move $a0, $t0    # print($t0)
    syscall
    # t40 = (str)" " -> str4
    li $v0, 4    # print string
    la $a0, str4    # print(t40)
    syscall
    j L8    # goto L8
L8:
    j L0    # goto L0
L2:
    # t41 = (str)"FIN WHILE" -> str8
    li $v0, 4    # print string
    la $a0, str8    # print(t41)
    syscall

    # === EPÍLOGO func_main ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO func_main ===