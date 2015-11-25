; sum an array
       go   0
0      ldi  3 .arr1     ; r3 points to first value
       ldi  4 .arr2     ; r4 points to first value
       ldi  1 0       ; r1 contains sum
       ld   2 .count     ; r2 has value of counter
.loop  add  1 *3      ; r1 = r1 + r3 next array value
       sub  1 *4		; r1 = r1 - r4 next array value
       inc  3
       inc  4
       dec  2
       bnz  2 .loop
       st	1 90
       sys  1 60
       dw   0 
.count dw   5
.arr1  dw   5
       dw   6
       dw   10
       dw   11
       dw   100
.arr2  dw   4
       dw   2
       dw   2
       dw   2
       dw   2
60     dw   0
       end
