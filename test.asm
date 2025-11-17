.data
str0: .asciiz " deposit="
str1: .asciiz " transfer from "
str2: .asciiz " to "
str3: .asciiz " amount="
str4: .asciiz " insufficient balance"
str5: .asciiz "Account "
str6: .asciiz " balance="
str7: .asciiz "Bank "
str8: .asciiz " charging fee="
str9: .asciiz "Alice"
str10: .asciiz "Bob"
str11: .asciiz "MyBank"

.text
.globl main

main:
    # Llamar a func_main (tu función principal)
    jal func_main

    # Salir del programa (syscall exit)
    li $v0, 10
    syscall

Account_method_constructor:
    # === PRÓLOGO Account_method_constructor ===
    addiu $sp, $sp, -8
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO Account_method_constructor ===

    # === CUERPO ===
    # Function Account_method_constructor body
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Account)
    move $t0, $a0    # $t0 = param[0]
    move $t1, $a1    # $t1 = param[1]
    move $t2, $a2    # $t2 = param[2]
    move $t3, $t1    # t0 = owner
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Account)
    li $t4, 0
    add $t5, $t0, $t4    # t1 = self + 0
    sw $t3, 0($t5)
    move $t6, $t2    # t2 = initial
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Account)
    li $t7, 4
    add $t8, $t0, $t7    # t3 = self + 4
    sw $t6, 0($t8)

    # === EPÍLOGO Account_method_constructor ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO Account_method_constructor ===


Account_method_deposit:
    # === PRÓLOGO Account_method_deposit ===
    addiu $sp, $sp, -8
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO Account_method_deposit ===

    # === CUERPO ===
    # Function Account_method_deposit body
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Account)
    move $t0, $a0    # $t0 = param[0]
    move $t1, $a1    # $t1 = param[1]
    li $t2, 4
    add $t3, $t0, $t2    # t4 = self + 4
    lw $t4, 0($t3)
    move $t5, $t4    # t6 = t5
    move $t6, $t1    # t7 = amount
    add $t7, $t5, $t6    # t8 = t6 + t7
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Account)
    li $t2, 4
    add $t8, $t0, $t2    # t9 = self + 4
    sw $t7, 0($t8)
    la $t9, str0     # t10 = &" deposit="
    li $v0, 4    # print string
    la $a0, str0    # print(t10)
    syscall
    move $s0, $t1    # t11 = amount
    li $v0, 1    # print int
    move $a0, $s0    # print($s0)
    syscall

    # === EPÍLOGO Account_method_deposit ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO Account_method_deposit ===


Account_method_transferTo:
    # === PRÓLOGO Account_method_transferTo ===
    addiu $sp, $sp, -8
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO Account_method_transferTo ===

    # === CUERPO ===
    # Function Account_method_transferTo body
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Account)
    move $t0, $a0    # $t0 = param[0]
    move $t1, $a1    # $t1 = param[1]
    move $t2, $a2    # $t2 = param[2]
    la $t3, str1     # t12 = &" transfer from "
    li $t4, 0
    add $t5, $t0, $t4    # t13 = self + 0
    lw $t6, 0($t5)
    move $t7, $t6    # t15 = t14
    add $t8, $t3, $t7    # t16 = t12 + t15
    li $v0, 4    # print string
    la $a0, str1    # print(t12)
    syscall
    li $v0, 4    # print string (fallback)
    move $a0, $t7    # print($t7)
    syscall
    la $t9, str2     # t17 = &" to "
    li $t4, 0
    add $s0, $t1, $t4    # t18 = other + 0
    lw $s1, 0($s0)
    move $s2, $s1    # t20 = t19
    add $s3, $t9, $s2    # t21 = t17 + t20
    li $v0, 4    # print string
    la $a0, str2    # print(t17)
    syscall
    li $v0, 4    # print string (fallback)
    move $a0, $s2    # print($s2)
    syscall
    la $s4, str3     # t22 = &" amount="
    li $v0, 4    # print string
    la $a0, str3    # print(t22)
    syscall
    move $s5, $t2    # t23 = amount
    li $v0, 1    # print int
    move $a0, $s5    # print($s5)
    syscall
    move $s6, $t2    # t24 = amount
    li $s7, 4
    sw $t3, -52($fp)    # spill t12
    add $t3, $t0, $s7    # t25 = self + 4
    sw $t3, -76($fp)    # spill t25
    lw $t3, 0($t3)
    sw $t3, -100($fp)    # spill t26
    sw $t3, -28($fp)    # spill t27
    sgt $t3, $s6, $t3    # t28 = t24 > t27
    bne $t3, $zero, L0    # if t28 goto L0
    j L1    # goto L1
L0:
    sw $t0, -16($fp)    # spill self
    la $t0, str4     # t29 = &" insufficient balance"
    li $v0, 4    # print string
    la $a0, str4    # print(t29)
    syscall
    j L2    # goto L2
L1:
    sw $t0, -116($fp)    # spill t29
    lw $t0, -16($fp)    # load self
    li $s7, 4
    sw $t3, -112($fp)    # spill t28
    add $t3, $t0, $s7    # t30 = self + 4
    sw $t3, -32($fp)    # spill t30
    lw $t3, 0($t3)
    sw $t3, -80($fp)    # spill t31
    move $t4, $t2    # t33 = amount
    sw $t3, -88($fp)    # spill t32
    sub $t3, $t3, $t4    # t34 = t32 - t33
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Account)
    li $s7, 4
    add $t0, $t0, $s7    # t35 = self + 4
    sw $t3, 0($t0)
    li $s7, 4
    sw $t0, -36($fp)    # spill t35
    add $t0, $t1, $s7    # t36 = other + 4
    sw $t0, -12($fp)    # spill t36
    lw $t0, 0($t0)
    sw $t0, -104($fp)    # spill t37
    sw $t2, -20($fp)    # spill amount
    sw $t0, -96($fp)    # spill t38
    add $t0, $t0, $t2    # t40 = t38 + t39
    li $s7, 4
    sw $t1, -108($fp)    # spill other
    add $t1, $t1, $s7    # t41 = other + 4
    sw $t0, 0($t1)
    j L2    # goto L2
L2:

    # === EPÍLOGO Account_method_transferTo ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO Account_method_transferTo ===


Account_method_printInfo:
    # === PRÓLOGO Account_method_printInfo ===
    addiu $sp, $sp, -8
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO Account_method_printInfo ===

    # === CUERPO ===
    # Function Account_method_printInfo body
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Account)
    move $t0, $a0    # $t0 = param[0]
    la $t1, str5     # t42 = &"Account "
    li $t2, 0
    add $t3, $t0, $t2    # t43 = self + 0
    lw $t4, 0($t3)
    move $t5, $t4    # t45 = t44
    add $t6, $t1, $t5    # t46 = t42 + t45
    li $v0, 4    # print string
    la $a0, str5    # print(t42)
    syscall
    li $v0, 4    # print string (fallback)
    move $a0, $t5    # print($t5)
    syscall
    la $t7, str6     # t47 = &" balance="
    li $v0, 4    # print string
    la $a0, str6    # print(t47)
    syscall
    li $t8, 4
    add $t9, $t0, $t8    # t48 = self + 4
    lw $s0, 0($t9)
    move $s1, $s0    # t50 = t49
    li $v0, 1    # print int
    move $a0, $s1    # print($s1)
    syscall

    # === EPÍLOGO Account_method_printInfo ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO Account_method_printInfo ===


Bank_method_constructor:
    # === PRÓLOGO Bank_method_constructor ===
    addiu $sp, $sp, -8
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO Bank_method_constructor ===

    # === CUERPO ===
    # Function Bank_method_constructor body
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Bank)
    move $t0, $a0    # $t0 = param[0]
    move $t1, $a1    # $t1 = param[1]
    move $t2, $a2    # $t2 = param[2]
    move $t3, $t1    # t51 = name
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Bank)
    li $t4, 0
    add $t5, $t0, $t4    # t52 = self + 0
    sw $t3, 0($t5)
    move $t6, $t2    # t53 = fee
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Bank)
    li $t7, 4
    add $t8, $t0, $t7    # t54 = self + 4
    sw $t6, 0($t8)

    # === EPÍLOGO Bank_method_constructor ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO Bank_method_constructor ===


Bank_method_chargeMonthlyFee:
    # === PRÓLOGO Bank_method_chargeMonthlyFee ===
    addiu $sp, $sp, -8
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO Bank_method_chargeMonthlyFee ===

    # === CUERPO ===
    # Function Bank_method_chargeMonthlyFee body
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Bank)
    move $t0, $a0    # $t0 = param[0]
    move $t1, $a1    # $t1 = param[1]
    la $t2, str7     # t55 = &"Bank "
    li $t3, 0
    add $t4, $t0, $t3    # t56 = self + 0
    lw $t5, 0($t4)
    move $t6, $t5    # t58 = t57
    add $t7, $t2, $t6    # t59 = t55 + t58
    li $v0, 4    # print string
    la $a0, str7    # print(t55)
    syscall
    li $v0, 4    # print string (fallback)
    move $a0, $t6    # print($t6)
    syscall
    la $t8, str8     # t60 = &" charging fee="
    li $v0, 4    # print string
    la $a0, str8    # print(t60)
    syscall
    li $t9, 4
    add $s0, $t0, $t9    # t61 = self + 4
    lw $s1, 0($s0)
    move $s2, $s1    # t63 = t62
    li $v0, 1    # print int
    move $a0, $s2    # print($s2)
    syscall
    move $a0, $t1    # param[0] = account
    move $s3, $t1    # t64 = account
    li $t9, 4
    add $s4, $t0, $t9    # t65 = self + 4
    lw $s5, 0($s4)
    move $s6, $s5    # t67 = t66
    move $a1, $s3    # param[1] = t64
    move $a2, $s6    # param[2] = t67
    jal Account_method_transferTo   # call Account_method_transferTo()
    move $s7, $v0    # ret of Account_method_transferTo()
    sw $t0, -28($fp)    # spill self
    move $t0, $s7    # t69 = t68

    # === EPÍLOGO Bank_method_chargeMonthlyFee ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO Bank_method_chargeMonthlyFee ===


func_main:
    # === PRÓLOGO func_main ===
    addiu $sp, $sp, -160
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO func_main ===

    # === CUERPO ===
    # Function func_main body
    # TODO: unsupported TAC op nop (    # init Account)
    li $a0, 8    # bytes a reservar
    li $v0, 9    # sbrk - alloc
    syscall
    move $t0, $v0    # t70 = puntero objeto
    move $a0, $t0    # param[0] = t70
    la $t1, str9     # t71 = &"Alice"
    li $t2, 10    # t72 = 10
    move $a1, $t1    # param[1] = t71
    move $a2, $t2    # param[2] = t72
    jal Account_method_constructor   # call Account_method_constructor()
    # TODO: unsupported TAC op nop (    # finished init Account)     
    move $t3, $t0    # t73 = t70
    move $t4, $t3    # a = t73
    # TODO: unsupported TAC op nop (    # init Account)
    li $a0, 8    # bytes a reservar
    li $v0, 9    # sbrk - alloc
    syscall
    move $t5, $v0    # t74 = puntero objeto
    move $a0, $t5    # param[0] = t74
    la $t6, str10     # t75 = &"Bob"
    li $t7, 5    # t76 = 5
    move $a1, $t6    # param[1] = t75
    move $a2, $t7    # param[2] = t76
    jal Account_method_constructor   # call Account_method_constructor()
    # TODO: unsupported TAC op nop (    # finished init Account)     
    move $t8, $t5    # t77 = t74
    move $t9, $t8    # b = t77
    # TODO: unsupported TAC op nop (    # init Bank)
    li $a0, 8    # bytes a reservar
    li $v0, 9    # sbrk - alloc
    syscall
    move $s0, $v0    # t78 = puntero objeto
    move $a0, $s0    # param[0] = t78
    la $s1, str11     # t79 = &"MyBank"
    li $s2, 1    # t80 = 1
    move $a1, $s1    # param[1] = t79
    move $a2, $s2    # param[2] = t80
    jal Bank_method_constructor   # call Bank_method_constructor()   
    # TODO: unsupported TAC op nop (    # finished init Bank)        
    move $s3, $s0    # t81 = t78
    move $s4, $s3    # bank = t81
    move $a0, $t4    # param[0] = a
    jal Account_method_printInfo   # call Account_method_printInfo() 
    move $s5, $v0    # ret of Account_method_printInfo()
    move $s6, $s5    # t83 = t82
    move $a0, $t9    # param[0] = b
    jal Account_method_printInfo   # call Account_method_printInfo() 
    move $s7, $v0    # ret of Account_method_printInfo()
    sw $t0, -40($fp)    # spill t70
    move $t0, $s7    # t85 = t84
    move $a0, $t4    # param[0] = a
    sw $t0, -8($fp)    # spill t85
    li $t0, 3    # t86 = 3
    move $a1, $t0    # param[1] = t86
    jal Account_method_deposit   # call Account_method_deposit()     
    sw $t0, -80($fp)    # spill t86
    move $t0, $v0    # ret of Account_method_deposit()
    move $a0, $t4    # param[0] = a
    jal Account_method_printInfo   # call Account_method_printInfo() 
    sw $t0, -44($fp)    # spill t88
    move $t0, $v0    # ret of Account_method_printInfo()
    move $a0, $t4    # param[0] = a
    sw $t0, -32($fp)    # spill t90
    move $t0, $t9    # t91 = b
    sw $t0, -24($fp)    # spill t91
    li $t0, 5    # t92 = 5
    sw $t0, -12($fp)    # spill t92
    lw $t0, -24($fp)    # load t91
    move $a1, $t0    # param[1] = t91
    lw $t0, -12($fp)    # load t92
    move $a2, $t0    # param[2] = t92
    jal Account_method_transferTo   # call Account_method_transferTo()
    move $t0, $v0    # ret of Account_method_transferTo()
    move $a0, $t4    # param[0] = a
    jal Account_method_printInfo   # call Account_method_printInfo() 
    sw $t0, -52($fp)    # spill t94
    move $t0, $v0    # ret of Account_method_printInfo()
    move $a0, $t9    # param[0] = b
    jal Account_method_printInfo   # call Account_method_printInfo() 
    sw $t0, -132($fp)    # spill t96
    move $t0, $v0    # ret of Account_method_printInfo()
    move $a0, $s4    # param[0] = bank
    sw $t0, -136($fp)    # spill t98
    move $t0, $t4    # t99 = a
    move $a1, $t0    # param[1] = t99
    jal Bank_method_chargeMonthlyFee   # call Bank_method_chargeMonthlyFee()
    sw $t0, -120($fp)    # spill t99
    move $t0, $v0    # ret of Bank_method_chargeMonthlyFee()
    move $a0, $t4    # param[0] = a
    jal Account_method_printInfo   # call Account_method_printInfo() 
    sw $t0, -96($fp)    # spill t101
    move $t0, $v0    # ret of Account_method_printInfo()

    # === EPÍLOGO func_main ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 160
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO func_main ===