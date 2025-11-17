.data
str0: .asciiz "i="
str1: .asciiz " j="
str2: .asciiz " s="
str3: .asciiz " total before="
str4: .asciiz " total="
str6: .asciiz " | "
str7: .asciiz " [end outer iteration] "
str8: .asciiz "FINAL TOTAL="

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
    move $t1, $t0    # total = t0
    li $t2, 0    # t1 = 0
    move $t3, $t2    # i = t1
L0:
    move $t4, $t3    # t2 = i
    li $t5, 3    # t3 = 3
    slt $t6, $t4, $t5    # t4 = t2 < t3
    bne $t6, $zero, L1    # if t4 goto L1
    j L3    # goto L3
L1:
    li $t7, 0    # t8 = 0
    move $t8, $t7    # j = t8
L4:
    move $t9, $t8    # t9 = j
    li $s0, 3    # t10 = 3
    slt $s1, $t9, $s0    # t11 = t9 < t10
    bne $s1, $zero, L5    # if t11 goto L5
    j L7    # goto L7
L5:
    move $s2, $t3    # t15 = i
    move $s3, $t8    # t16 = j
    add $s4, $s2, $s3    # t17 = t15 + t16
    move $s5, $s4    # s = t17
    # t18 = (str)"i=" -> str0
    li $v0, 4    # print string
    la $a0, str0    # print(t18)
    syscall
    move $s6, $t3    # t19 = i
    li $v0, 1    # print int
    move $a0, $s6    # print($s6)
    syscall
    # t20 = (str)" j=" -> str1
    li $v0, 4    # print string
    la $a0, str1    # print(t20)
    syscall
    move $s7, $t8    # t21 = j
    li $v0, 1    # print int
    move $a0, $s7    # print($s7)
    syscall
    # WARNING: cannot spill t0 from $t0 (no offset)
    move $t0, $s5    # t22 = s
    # WARNING: cannot spill t1 from $t2 (no offset)
    li $t2, 2    # t23 = 2
    # WARNING: cannot spill t22 from $t0 (no offset)
    sgt $t0, $t0, $t2    # t24 = t22 > t23
    bne $t0, $zero, L8    # if t24 goto L8
    j L9    # goto L9
L8:
    # t25 = (str)" s=" -> str2
    li $v0, 4    # print string
    la $a0, str2    # print(t25)
    syscall
    # WARNING: cannot spill t24 from $t0 (no offset)
    move $t0, $s5    # t26 = s
    li $v0, 1    # print int
    move $a0, $t0    # print($t0)
    syscall
    # t27 = (str)" total before=" -> str3
    li $v0, 4    # print string
    la $a0, str3    # print(t27)
    syscall
    # WARNING: cannot spill t26 from $t0 (no offset)
    move $t0, $t1    # t28 = total
    li $v0, 1    # print int
    move $a0, $t0    # print($t0)
    syscall
    # WARNING: cannot spill t28 from $t0 (no offset)
    move $t0, $t1    # t29 = total
    # WARNING: cannot spill total from $t1 (no offset)
    move $t1, $s5    # t30 = s
    # WARNING: cannot spill t29 from $t0 (no offset)
    add $t0, $t0, $t1    # t31 = t29 + t30
    # WARNING: cannot spill t31 from $t0 (no offset)
    # t32 = (str)" total=" -> str4
    li $v0, 4    # print string
    la $a0, str4    # print(t32)
    syscall
    # WARNING: cannot spill t30 from $t1 (no offset)
    move $t1, $t0    # t33 = total
    li $v0, 1    # print int
    move $a0, $t1    # print($t1)
    syscall
    j L10    # goto L10
L9:
    # t34 = (str)" s=" -> str2
    li $v0, 4    # print string
    la $a0, str2    # print(t34)
    syscall
    # WARNING: cannot spill t33 from $t1 (no offset)
    move $t1, $s5    # t35 = s
    li $v0, 1    # print int
    move $a0, $t1    # print($t1)
    syscall
    j L10    # goto L10
L10:
    # t36 = (str)" | " -> str6
    li $v0, 4    # print string
    la $a0, str6    # print(t36)
    syscall
    j L6    # goto L6
L6:
    # WARNING: cannot spill t35 from $t1 (no offset)
    move $t1, $t8    # t12 = j
    # WARNING: cannot spill t23 from $t2 (no offset)
    li $t2, 1    # t13 = 1
    # WARNING: cannot spill t12 from $t1 (no offset)
    add $t1, $t1, $t2    # t14 = t12 + t13
    move $t8, $t1    # j = t14
    j L4    # goto L4
L7:
    # t37 = (str)" [end outer iteration] " -> str7
    li $v0, 4    # print string
    la $a0, str7    # print(t37)
    syscall
    j L2    # goto L2
L2:
    # WARNING: cannot spill t14 from $t1 (no offset)
    move $t1, $t3    # t5 = i
    # WARNING: cannot spill t13 from $t2 (no offset)
    li $t2, 1    # t6 = 1
    # WARNING: cannot spill t5 from $t1 (no offset)
    add $t1, $t1, $t2    # t7 = t5 + t6
    move $t3, $t1    # i = t7
    j L0    # goto L0
L3:
    # t38 = (str)"FINAL TOTAL=" -> str8
    li $v0, 4    # print string
    la $a0, str8    # print(t38)
    syscall
    # WARNING: cannot spill total from $t0 (no offset)
    li $v0, 1    # print int
    move $a0, $t0    # print($t0)
    syscall

    # === EPÍLOGO func_main ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO func_main ===