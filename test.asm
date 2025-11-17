.data
str0: .asciiz "Hola "
str1: .asciiz "Diego"

.text
.globl main

main:
    # Llamar a func_main (tu función principal)
    jal func_main

    # Salir del programa (syscall exit)
    li $v0, 10
    syscall

Persona_method_constructor:
    # === PRÓLOGO Persona_method_constructor ===
    addiu $sp, $sp, -8
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO Persona_method_constructor ===

    # === CUERPO ===
    # Function Persona_method_constructor body
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Persona)
    move $t0, $a0    # $t0 = param[0]
    move $t1, $a1    # $t1 = param[1]
    move $t2, $a2    # $t2 = param[2]
    move $t3, $t1    # t0 = nombre
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Persona)
    li $t4, 0
    add $t5, $t0, $t4    # t1 = self + 0
    sw $t3, 0($t5)
    move $t6, $t2    # t2 = edad
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Persona)
    li $t7, 4
    add $t8, $t0, $t7    # t3 = self + 4
    sw $t6, 0($t8)

    # === EPÍLOGO Persona_method_constructor ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO Persona_method_constructor ===


Persona_method_saludar:
    # === PRÓLOGO Persona_method_saludar ===
    addiu $sp, $sp, -8
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO Persona_method_saludar ===

    # === CUERPO ===
    # Function Persona_method_saludar body
    # TODO: unsupported TAC op nop (    # Param 0 is reference to 'Self' for Persona)
    move $t0, $a0    # $t0 = param[0]
    la $t1, str0     # t4 = &"Hola "
    li $t2, 0
    add $t3, $t0, $t2    # t5 = self + 0
    lw $t4, 0($t3)
    move $t5, $t4    # t7 = t6
    add $t6, $t1, $t5    # t8 = t4 + t7
    li $v0, 4    # print string
    la $a0, str0    # print(t4)
    syscall
    li $v0, 4    # print string (fallback)
    move $a0, $t5    # print($t5)
    syscall

    # === EPÍLOGO Persona_method_saludar ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 8
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO Persona_method_saludar ===


func_main:
    # === PRÓLOGO func_main ===
    addiu $sp, $sp, -40
    sw $ra, 0($sp)
    sw $fp, 4($sp)
    move $fp, $sp
    # === FIN PRÓLOGO func_main ===

    # === CUERPO ===
    # Function func_main body
    # TODO: unsupported TAC op nop (    # init Persona)
    li $a0, 8    # bytes a reservar
    li $v0, 9    # sbrk - alloc
    syscall
    move $t0, $v0    # t9 = puntero objeto
    move $a0, $t0    # param[0] = t9
    la $t1, str1     # t10 = &"Diego"
    li $t2, 21    # t11 = 21
    move $a1, $t1    # param[1] = t10
    move $a2, $t2    # param[2] = t11
    jal Persona_method_constructor   # call Persona_method_constructor()
    # TODO: unsupported TAC op nop (    # finished init Persona)     
    move $t3, $t0    # t12 = t9
    move $t4, $t3    # p = t12
    move $a0, $t4    # param[0] = p
    jal Persona_method_saludar   # call Persona_method_saludar()     
    move $t5, $v0    # ret of Persona_method_saludar()
    move $t6, $t5    # t14 = t13

    # === EPÍLOGO func_main ===
    lw $fp, 4($sp)
    lw $ra, 0($sp)
    addiu $sp, $sp, 40
    jr $ra      # ret en $v0
    # === FIN EPÍLOGO func_main ===